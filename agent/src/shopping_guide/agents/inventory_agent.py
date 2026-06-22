"""InventoryAgent — real-time stock validation and purchase limits.

Validates stock levels for candidate products, generates low-stock alerts,
and computes dynamic purchase limits based on stock depth and product heat.

Adapted from refer/multi-agent-ecommerce-system/python/agents/inventory_agent.py
"""

from __future__ import annotations

import logging
from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import InventoryResult, Product

logger = logging.getLogger(__name__)


class InventoryAgent(BaseAgent):
    """Validates stock levels and computes purchase limits.

    Queries marketplace backend for real-time stock data when available,
    with configurable safety/low-stock thresholds.
    """

    def __init__(self, http_client: Any = None):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="inventory",
            timeout=settings.sg_agent_timeout_inventory,
        )
        self.http = http_client
        self.safety_stock = settings.sg_safety_stock_threshold
        self.low_stock = settings.sg_low_stock_threshold

    async def _execute(self, **kwargs: Any) -> InventoryResult:
        products: list[Product] = kwargs.get("products", [])

        available: list[str] = []
        low_stock_alerts: list[dict[str, Any]] = []
        purchase_limits: dict[str, int] = {}

        for product in products:
            stock = await self._check_stock(product)

            if stock <= 0:
                logger.info("inventory: out of stock product=%s", product.product_id)
                continue

            available.append(product.product_id)

            if stock <= self.safety_stock:
                low_stock_alerts.append({
                    "product_id": product.product_id,
                    "name": product.name,
                    "current_stock": stock,
                    "level": "critical",
                    "action": "urgent_restock",
                })
            elif stock <= self.low_stock:
                low_stock_alerts.append({
                    "product_id": product.product_id,
                    "name": product.name,
                    "current_stock": stock,
                    "level": "warning",
                    "action": "plan_restock",
                })

            limit = self._calc_purchase_limit(product, stock)
            if limit is not None:
                purchase_limits[product.product_id] = limit

        return InventoryResult(
            success=True,
            available_products=available,
            low_stock_alerts=low_stock_alerts,
            purchase_limits=purchase_limits,
            data={
                "total_checked": len(products),
                "available_count": len(available),
                "alert_count": len(low_stock_alerts),
                "limited_count": len(purchase_limits),
            },
            confidence=0.95,
        )

    async def _check_stock(self, product: Product) -> int:
        """Get real-time stock — try backend API, fall back to cached value."""
        if self.http:
            try:
                result = await self.http.get(
                    f"/api/v1/portal/products/{product.product_id}",
                    timeout=4.0,
                )
                stock = int(result.get("stock", 0) or 0)
                return stock
            except Exception as exc:
                logger.warning(
                    "inventory: API stock check failed for %s: %s",
                    product.product_id,
                    exc,
                )
        return product.stock  # fallback to cached stock from recall

    def _calc_purchase_limit(self, product: Product, stock: int) -> int | None:
        """Dynamic purchase limit based on stock depth and product heat.

        Rules:
          - stock <= safety_stock: limit 1 (all products)
          - stock <= low_stock + hot (新品/旗舰/热销): limit 2
          - hot + stock <= 300: limit 3
          - otherwise: no limit (None)
        """
        hot_tags = {"新品", "旗舰", "热销", "爆款"}
        is_hot = bool(set(product.tags) & hot_tags) or product.sale_count > 500

        if stock <= self.safety_stock:
            return 1
        if stock <= self.low_stock and is_hot:
            return 2
        if is_hot and stock <= 300:
            return 3
        return None
