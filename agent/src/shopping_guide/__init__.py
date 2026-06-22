"""Shopping Guide Agent System — multi-agent e-commerce recommendation.

Based on the Supervisor-specialist pattern with 4 agents running in a
3-phase parallel pipeline:

  Phase 1 (parallel):   UserProfileAgent + ProductRecAgent (recall)
  Phase 2 (parallel):   ProductRecAgent (rerank) + InventoryAgent
  Filter:               Stock-aware candidate filtering
  Phase 3 (serial):     MarketingCopyAgent (personalized copy + compliance)

Usage:
    from shopping_guide.orchestrator.supervisor import ShoppingGuideSupervisor

    supervisor = ShoppingGuideSupervisor(llm_adapter=adapter, http_client=client)
    response = await supervisor.recommend(request)

Author: SnapTrip Team
Date: 2026-06-22
"""

from shopping_guide.orchestrator.supervisor import ShoppingGuideSupervisor
from shopping_guide.models.schemas import RecommendationRequest, RecommendationResponse

__all__ = [
    "ShoppingGuideSupervisor",
    "RecommendationRequest",
    "RecommendationResponse",
]
