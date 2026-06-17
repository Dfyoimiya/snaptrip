"""InventoryAgent —— 库存检查 Agent。

纯逻辑 Agent (无 LLM 调用), 对推荐商品执行实时库存验证:
  - 过滤缺货/下架商品
  - 设置每人限购量 (库存<50限1件, 热销品库存<100限2件)
  - 生成低库存预警

参考 multi-agent-ecommerce-system 的 InventoryAgent (纯规则引擎) 模式。
"""

from __future__ import annotations

import logging
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent

logger = logging.getLogger(__name__)

# 库存阈值常量
SAFETY_STOCK_THRESHOLD = 50   # 低于此值视为低库存
LOW_STOCK_THRESHOLD = 100     # 低于此值触发预警
HOT_ITEM_PURCHASE_LIMIT = 3   # 热销品限购
CRITICAL_STOCK_LIMIT = 1      # 极低库存限购


class InventoryAgent(BaseRecommendationAgent):
    """库存检查 Agent —— 纯逻辑, 不消耗 LLM Token。"""

    agent_name = "inventory"
    max_retries = 1
    timeout = 5.0

    def __init__(self, db_session_factory: Any = None) -> None:
        super().__init__()
        self._db_factory = db_session_factory

    async def _execute(self, **kwargs: Any) -> AgentResult:
        products = kwargs.get("products", [])
        if not products:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data={"available_products": [], "low_stock_alerts": [], "purchase_limits": {}},
                confidence=0.95,
            )

        available: list[dict] = []
        low_stock_alerts: list[dict] = []
        purchase_limits: dict[str, int] = {}

        for product in products:
            stock = product.get("stock", 0)
            product_id = product.get("product_id", "")
            is_published = product.get("publish_status", 1)
            is_verified = product.get("verify_status", 1)

            # 过滤未发布/未审核商品
            if not is_published or not is_verified:
                continue

            # 过滤缺货商品
            if stock <= 0:
                continue

            # 库存检查
            is_hot = self._is_hot_product(product)
            limit = self._calc_purchase_limit(stock, is_hot)
            if limit is not None:
                purchase_limits[product_id] = limit

            # 低库存预警
            if stock <= SAFETY_STOCK_THRESHOLD:
                low_stock_alerts.append({
                    "product_id": product_id,
                    "product_name": product.get("name", ""),
                    "current_stock": stock,
                    "threshold": SAFETY_STOCK_THRESHOLD,
                    "is_hot": is_hot,
                })

            available.append({**product, "stock": stock, "is_hot": is_hot})

        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            data={
                "available_products": available,
                "low_stock_alerts": low_stock_alerts,
                "purchase_limits": purchase_limits,
                "filtered_out": len(products) - len(available),
            },
            confidence=0.95,
        )

    @staticmethod
    def _is_hot_product(product: dict) -> bool:
        """判断是否为热销品。"""
        tags = product.get("tags", [])
        if isinstance(tags, list):
            tag_names = [t.lower() if isinstance(t, str) else t.get("name", "").lower() for t in tags]
        else:
            tag_names = []
        hot_keywords = {"新品", "热销", "旗舰", "爆款", "new", "hot", "flagship", "bestseller"}
        name = (product.get("name") or "").lower()
        sale_count = product.get("sale_count", 0)
        return bool(
            any(kw in name for kw in hot_keywords)
            or any(kw in tag for kw in hot_keywords for tag in tag_names)
            or sale_count > 500
        )

    @staticmethod
    def _calc_purchase_limit(stock: int, is_hot: bool) -> int | None:
        """计算每人限购数量。"""
        if stock <= SAFETY_STOCK_THRESHOLD:
            return CRITICAL_STOCK_LIMIT
        if is_hot and stock <= LOW_STOCK_THRESHOLD:
            return HOT_ITEM_PURCHASE_LIMIT
        return None  # 不限购
