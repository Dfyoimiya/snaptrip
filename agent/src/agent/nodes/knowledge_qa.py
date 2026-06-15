"""Knowledge QA — FAQ, general questions, store policies."""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

KNOWLEDGE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the SnapTrip knowledge base for FAQs, policies, "
            "and general information. Covers payment methods, account management, "
            "store locations, cancellation policies, insurance, visa requirements, "
            "and general travel tips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query for the knowledge base",
                    },
                    "topic": {
                        "type": "string",
                        "enum": [
                            "payment",
                            "account",
                            "cancellation",
                            "insurance",
                            "visa",
                            "store",
                            "general",
                            "all",
                        ],
                        "description": "Topic filter to narrow results (default: 'all')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3, max: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

KNOWLEDGE_SYSTEM_PROMPT = """You are a knowledgeable customer service agent for SnapTrip, a travel e-commerce platform.

Your job is to answer general questions about SnapTrip's services, policies, and travel-related topics.

Guidelines:
1. Use 'search_knowledge' to look up answers in the knowledge base. Always search
   before answering factual questions — do not guess or fabricate information.
2. If the knowledge base returns relevant information, summarize it clearly for the user.
3. If the question is beyond what the knowledge base covers, be honest and suggest
   contacting human support or visiting the website for more details.
4. Common topics include: payment methods, account registration, cancellation policies,
   insurance options, visa requirements, store locations, and general travel tips.
5. Be polite, concise, and helpful.
6. NEVER call a tool that you don't have defined.

When providing a final answer (without tool calls), structure your response as JSON:
{"answer": "Your knowledge base answer here", "highlights": ["Key fact 1", "Key fact 2"]}

Respond in the user's language.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class KnowledgeQANode(BaseSpecialist):
    node_name = "knowledge_qa"
    system_prompt = KNOWLEDGE_SYSTEM_PROMPT
    tools = KNOWLEDGE_TOOLS
    phase_name = "knowledge_qa"
    temperature = 0.3


_instance = KnowledgeQANode()


async def knowledge_qa_node(state: PlanState) -> dict:
    """Answer general questions. Calls search_knowledge tool.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return cast(dict, await _instance.execute(state))
