"""SnapTrip agent nodes — Supervisor + specialist agents + synthesis."""

from agent.nodes.supervisor import route_by_intent, supervisor_node
from agent.nodes.product_discovery import product_discovery_node
from agent.nodes.order_assistant import order_assistant_node
from agent.nodes.marketing_engine import marketing_engine_node
from agent.nodes.knowledge_qa import knowledge_qa_node
from agent.nodes.admin_analyst import admin_analyst_node
from agent.nodes.synthesize import synthesize_node

__all__ = [
    "supervisor_node",
    "route_by_intent",
    "product_discovery_node",
    "order_assistant_node",
    "marketing_engine_node",
    "knowledge_qa_node",
    "admin_analyst_node",
    "synthesize_node",
]
