"""C-end个性化推荐 Agent 包。

参考 multi-agent-ecommerce-system 的 4-Agent 并行编排模式:
  UserProfileAgent → ProductRecAgent → InventoryAgent → MarketingCopyAgent

编排流程:
  1. Supervisor 接收推荐请求 (user_id + scene)
  2. Phase 1 (并行): UserProfileAgent 画像分析 || ProductRecAgent 多策略召回
  3. Phase 2 (并行): ProductRecAgent LLM重排 || InventoryAgent 库存过滤
  4. Phase 3 (串行): MarketingCopyAgent 生成个性化文案
  5. 返回 RecommendationResponse (products + copies + trace_id)

各 Agent 继承 BaseRecommendationAgent (适配自 BaseSpecialist),
支持 retry/timeout/fallback, 单个 Agent 失败不影响整体推荐结果。
"""

from agent.nodes.recommendation.supervisor import RecommendationSupervisor  # noqa: F401

__all__ = ["RecommendationSupervisor"]
