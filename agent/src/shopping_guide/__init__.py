"""Shopping Guide Agent System — multi-agent e-commerce recommendation + information search.

Based on the Supervisor-specialist pattern with 4 agents running in a
3-phase parallel pipeline:

  Phase 1 (parallel):   UserProfileAgent + ProductRecAgent (recall)
  Phase 2 (parallel):   ProductRecAgent (rerank) + InventoryAgent
  Filter:               Stock-aware candidate filtering
  Phase 3 (serial):     MarketingCopyAgent (personalized copy + compliance)

New: Information Search pipeline with WebSearchAgent + ReviewSearchAgent
  Phase 1 (parallel):   WebSearchAgent + ReviewSearchAgent
  Phase 2 (serial):     LLM structured synthesis → canvas cards

Usage:
    from shopping_guide import (
        ShoppingGuideSupervisor,
        InfoSearchSupervisor,
        GuideRouter,
    )

    supervisor = ShoppingGuideSupervisor(llm_adapter=adapter, http_client=client)
    response = await supervisor.recommend(request)

    info_sup = InfoSearchSupervisor(llm_adapter=adapter, http_client=client)
    info_response = await info_sup.search(info_request)

    router = GuideRouter(llm_adapter=adapter, shopping_supervisor=supervisor,
                         info_search_supervisor=info_sup)
    result = await router.route(routed_request)

Author: SnapTrip Team
Date: 2026-06-23
"""

from shopping_guide.orchestrator.supervisor import ShoppingGuideSupervisor
from shopping_guide.orchestrator.info_search_supervisor import InfoSearchSupervisor
from shopping_guide.orchestrator.guide_router import GuideRouter
from shopping_guide.models.schemas import (
    GuideIntent,
    InfoSearchRequest,
    InfoSearchResponse,
    RecommendationRequest,
    RecommendationResponse,
    RoutedRequest,
)

__all__ = [
    "GuideIntent",
    "GuideRouter",
    "InfoSearchRequest",
    "InfoSearchResponse",
    "InfoSearchSupervisor",
    "RecommendationRequest",
    "RecommendationResponse",
    "RoutedRequest",
    "ShoppingGuideSupervisor",
]
