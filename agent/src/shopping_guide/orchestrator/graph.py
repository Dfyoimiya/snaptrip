"""LangGraph state graph wrapper for the shopping guide pipeline.

Provides a LangGraph-based alternative to the raw supervisor.recommend() call,
enabling checkpointing, streaming, and integration with our existing graph
management infrastructure.

DAG:
  init → parallel_phase1 → parallel_phase2 → filter → marketing_copy → aggregate → END

Adapted from refer/multi-agent-ecommerce-system/python/orchestrator/graph.py
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from shopping_guide.agents import (
    InventoryAgent,
    MarketingCopyAgent,
    ProductRecAgent,
    UserProfileAgent,
)
from shopping_guide.models.schemas import Product, UserProfile
from shopping_guide.services.ab_test import ABTestEngine

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    """State that flows through the shopping guide LangGraph pipeline."""

    request_id: str
    user_id: str
    scene: str
    message: str
    num_items: int
    context: dict[str, Any]
    experiment_group: str

    user_profile: UserProfile | None
    raw_products: list[Product]
    ranked_products: list[Product]
    available_ids: set[str]
    final_products: list[Product]
    marketing_copies: list[dict[str, str]]

    agent_results: dict[str, Any]
    total_latency_ms: float
    _start_time: float


async def init_node(state: PipelineState) -> PipelineState:
    """Initialise pipeline state with request ID and A/B assignment."""
    state["request_id"] = str(uuid.uuid4())[:8]
    state["_start_time"] = time.perf_counter()
    state["agent_results"] = {}
    return state


async def parallel_phase1(state: PipelineState) -> PipelineState:
    """Run UserProfile + ProductRec (recall) in parallel."""
    user_profile_agent = _get_agent("user_profile")
    product_rec_agent = _get_agent("product_rec")

    profile_result, rec_result = await asyncio.gather(
        user_profile_agent.run(
            user_id=state["user_id"],
            context=state.get("context", {}),
        ),
        product_rec_agent.run(
            user_profile=None,
            num_items=state.get("num_items", 10) * 2,
            query=state.get("message", ""),
            scene=state.get("scene", "homepage"),
        ),
    )

    state["user_profile"] = getattr(profile_result, "profile", None)
    state["raw_products"] = getattr(rec_result, "products", [])
    state["agent_results"]["user_profile"] = profile_result
    state["agent_results"]["product_recall"] = rec_result
    return state


async def parallel_phase2(state: PipelineState) -> PipelineState:
    """Run ProductRec (rerank) + Inventory in parallel."""
    product_rec_agent = _get_agent("product_rec")
    inventory_agent = _get_agent("inventory")

    rerank_task = product_rec_agent.run(
        user_profile=state.get("user_profile"),
        num_items=state.get("num_items", 10),
    )
    inventory_task = inventory_agent.run(
        products=state.get("raw_products", []),
    )

    rerank_result, inventory_result = await asyncio.gather(rerank_task, inventory_task)

    state["ranked_products"] = getattr(
        rerank_result, "products", state.get("raw_products", [])
    )
    state["available_ids"] = set(
        getattr(inventory_result, "available_products", [])
    )
    state["agent_results"]["rerank"] = rerank_result
    state["agent_results"]["inventory"] = inventory_result
    return state


async def filter_node(state: PipelineState) -> PipelineState:
    """Stock-aware candidate filtering."""
    ranked = state.get("ranked_products", [])
    avail = state.get("available_ids", set())
    num = state.get("num_items", 10)

    final = [p for p in ranked if p.product_id in avail]
    if not final:
        final = ranked
    state["final_products"] = final[:num]
    return state


async def marketing_copy_node(state: PipelineState) -> PipelineState:
    """Generate personalised marketing copy."""
    marketing_copy_agent = _get_agent("marketing_copy")
    result = await marketing_copy_agent.run(
        user_profile=state.get("user_profile"),
        products=state.get("final_products", []),
    )
    copies = getattr(result, "copies", [])
    state["marketing_copies"] = copies
    state["agent_results"]["marketing_copy"] = result

    # Merge copies into products
    copy_map = {c.get("product_id", ""): c.get("copy", "") for c in copies}
    for p in state.get("final_products", []):
        if p.product_id in copy_map:
            p.marketing_copy = copy_map[p.product_id]
    return state


async def aggregate_node(state: PipelineState) -> PipelineState:
    """Final aggregation and timing."""
    state["total_latency_ms"] = (
        time.perf_counter() - state.get("_start_time", 0)
    ) * 1000
    return state


# ── Agent singleton cache (injected at build time) ──

_agents: dict[str, Any] = {}


def _get_agent(name: str) -> Any:
    return _agents[name]


def build_shopping_guide_graph(
    llm_adapter: Any = None,
    http_client: Any = None,
    ab_engine: ABTestEngine | None = None,
) -> StateGraph:
    """Build and compile the shopping guide LangGraph pipeline.

    Args:
        llm_adapter: LLM adapter for LLM calls
        http_client: Marketplace HTTP client for backend API calls
        ab_engine: A/B test engine for traffic splitting

    Returns:
        Compiled LangGraph StateGraph
    """
    # Inject agent singletons
    _agents["user_profile"] = UserProfileAgent(
        llm_adapter=llm_adapter, http_client=http_client
    )
    _agents["product_rec"] = ProductRecAgent(
        llm_adapter=llm_adapter, http_client=http_client
    )
    _agents["marketing_copy"] = MarketingCopyAgent(llm_adapter=llm_adapter)
    _agents["inventory"] = InventoryAgent(http_client=http_client)

    graph = StateGraph(PipelineState)

    graph.add_node("init", init_node)
    graph.add_node("parallel_phase1", parallel_phase1)
    graph.add_node("parallel_phase2", parallel_phase2)
    graph.add_node("filter", filter_node)
    graph.add_node("marketing_copy", marketing_copy_node)
    graph.add_node("aggregate", aggregate_node)

    graph.set_entry_point("init")
    graph.add_edge("init", "parallel_phase1")
    graph.add_edge("parallel_phase1", "parallel_phase2")
    graph.add_edge("parallel_phase2", "filter")
    graph.add_edge("filter", "marketing_copy")
    graph.add_edge("marketing_copy", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()
