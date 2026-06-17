"""推荐 LangGraph 工作流 — StateGraph 构建器。

提供与 RecommendationSupervisor 等效的 LangGraph 实现,
可与现有 agent/graph.py 中的 DAG 并行注册。

状态流:
  init → parallel_phase1 (user_profile + recall) → parallel_phase2 (rerank + inventory)
  → filter → marketing_copy → aggregate → END

参考 multi-agent-ecommerce-system 的 LangGraph 实现模式。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from agent.nodes.recommendation.inventory import InventoryAgent
from agent.nodes.recommendation.marketing_copy import MarketingCopyAgent
from agent.nodes.recommendation.product_rec import ProductRecAgent
from agent.nodes.recommendation.user_profile import UserProfileAgent
from agent.schemas.recommendation import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)


class RecommendationState(TypedDict, total=False):
    """推荐流水线状态。"""
    request_id: str
    user_id: str | None
    session_id: str | None
    scene: str
    num_items: int
    context: dict[str, Any]
    experiment_group: str

    # Agent 中间结果
    user_profile: dict | None
    raw_products: list[dict]
    ranked_products: list[dict]
    available_products: list[dict]
    low_stock_alerts: list[dict]
    purchase_limits: dict[str, int]
    marketing_copies: list[dict]

    # 汇总
    agent_results: dict[str, Any]
    total_latency_ms: float
    _start_time: float


async def _init_node(state: RecommendationState) -> dict:
    """初始化推荐流水线。"""
    state["request_id"] = str(uuid.uuid4())
    state["_start_time"] = time.perf_counter()
    state["agent_results"] = {}
    state["raw_products"] = []
    state["ranked_products"] = []
    return state


async def _parallel_phase1(state: RecommendationState) -> dict:
    """Phase 1: 并行 — UserProfile + ProductRec (recall)。"""
    user_id_str = state.get("user_id")
    import uuid as _uuid

    user_id = _uuid.UUID(user_id_str) if user_id_str else None

    # 使用全局 Agent 实例 (由 build_recommendation_graph 注入)
    from agent.nodes.recommendation.graph import _agents as agents

    user_profile_agent: UserProfileAgent = agents["user_profile"]
    product_rec_agent: ProductRecAgent = agents["product_rec"]
    num_items = state.get("num_items", 10)
    scene = state.get("scene", "homepage")

    import asyncio

    results = await asyncio.gather(
        user_profile_agent.run(user_id=user_id),
        product_rec_agent.run(num_items=num_items, recall_only=True, scene=scene),
        return_exceptions=True,
    )

    updates: dict = {}
    for i, result in enumerate(results):
        agent_name = ["user_profile", "product_rec"][i]
        if hasattr(result, "success") and result.success:
            state.setdefault("agent_results", {})[agent_name] = result
            if agent_name == "user_profile":
                updates["user_profile"] = result.data.get("profile")
            elif agent_name == "product_rec":
                updates["raw_products"] = result.data.get("products", [])
        else:
            state.setdefault("agent_results", {})[agent_name] = {
                "success": False, "error": str(result)
            }

    return updates


async def _parallel_phase2(state: RecommendationState) -> dict:
    """Phase 2: 并行 — ProductRec (rerank) + Inventory。"""
    from agent.nodes.recommendation.graph import _agents as agents

    product_rec_agent: ProductRecAgent = agents["product_rec"]
    inventory_agent: InventoryAgent = agents["inventory"]
    raw_products = state.get("raw_products", [])
    user_profile = state.get("user_profile")
    num_items = state.get("num_items", 10)
    scene = state.get("scene", "homepage")

    import asyncio

    results = await asyncio.gather(
        product_rec_agent.run(
            user_profile=user_profile,
            products=raw_products,
            num_items=num_items,
            recall_only=False,
            scene=scene,
        ),
        inventory_agent.run(products=raw_products),
        return_exceptions=True,
    )

    updates: dict = {}
    for i, result in enumerate(results):
        agent_name = ["product_rec", "inventory"][i]
        if hasattr(result, "success") and result.success:
            state.setdefault("agent_results", {})[agent_name] = result
            if agent_name == "product_rec":
                updates["ranked_products"] = result.data.get("products", raw_products)
            elif agent_name == "inventory":
                updates["available_products"] = result.data.get("available_products", [])
                updates["low_stock_alerts"] = result.data.get("low_stock_alerts", [])
                updates["purchase_limits"] = result.data.get("purchase_limits", {})

    return updates


async def _filter_node(state: RecommendationState) -> dict:
    """过滤: 交集 ranked_products ∩ available_products。"""
    ranked = state.get("ranked_products", [])
    available = state.get("available_products", [])

    if available:
        available_ids = {p.get("product_id") for p in available}
        ranked = [p for p in ranked if p.get("product_id") in available_ids]

    return {"ranked_products": ranked}


async def _marketing_copy_node(state: RecommendationState) -> dict:
    """Phase 3: 串行 — MarketingCopy 生成。"""
    from agent.nodes.recommendation.graph import _agents as agents

    marketing_agent: MarketingCopyAgent = agents["marketing_copy"]
    products = state.get("ranked_products", [])
    user_profile = state.get("user_profile")

    result = await marketing_agent.run(user_profile=user_profile, products=products)

    updates: dict = {}
    if hasattr(result, "success") and result.success:
        state.setdefault("agent_results", {})["marketing_copy"] = result
        updates["marketing_copies"] = result.data.get("copies", [])

    return updates


async def _aggregate_node(state: RecommendationState) -> dict:
    """汇总: 计算总延迟。"""
    t0 = state.get("_start_time", time.perf_counter())
    total_latency_ms = (time.perf_counter() - t0) * 1000
    return {"total_latency_ms": total_latency_ms}


# ── 全局 Agent 实例 ──
_agents: dict[str, Any] = {}


def build_recommendation_graph(
    llm_adapter: Any = None,
    db_factory: Any = None,
    feature_service: Any = None,
    es_client: Any = None,
) -> CompiledStateGraph:
    """构建推荐 LangGraph 工作流。

    图结构 (线性 DAG 含并行节点):
      init → parallel_phase1 → parallel_phase2 → filter → marketing_copy → aggregate → END
    """
    global _agents
    _agents = {
        "user_profile": UserProfileAgent(llm_adapter=llm_adapter, feature_service=feature_service),
        "product_rec": ProductRecAgent(llm_adapter=llm_adapter, db_session_factory=db_factory, es_client=es_client),
        "inventory": InventoryAgent(db_session_factory=db_factory),
        "marketing_copy": MarketingCopyAgent(llm_adapter=llm_adapter),
    }

    builder = StateGraph(RecommendationState)

    builder.add_node("init", _init_node)
    builder.add_node("parallel_phase1", _parallel_phase1)
    builder.add_node("parallel_phase2", _parallel_phase2)
    builder.add_node("filter", _filter_node)
    builder.add_node("marketing_copy", _marketing_copy_node)
    builder.add_node("aggregate", _aggregate_node)

    builder.set_entry_point("init")
    builder.add_edge("init", "parallel_phase1")
    builder.add_edge("parallel_phase1", "parallel_phase2")
    builder.add_edge("parallel_phase2", "filter")
    builder.add_edge("filter", "marketing_copy")
    builder.add_edge("marketing_copy", "aggregate")
    builder.add_edge("aggregate", END)

    return builder.compile()
