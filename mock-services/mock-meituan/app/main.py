"""Mock API 服务入口 —— 模拟美团本地生活 API。

端点:
    GET  /poi/search     - POI 搜索
    GET  /poi/queue      - 排队查询
    POST /order/prepare  - 下单准备
    POST /order/submit   - 下单提交
    POST /order/pay      - 支付
    GET  /route          - 路线规划
    GET  /weather        - 天气查询
    POST /delivery/schedule - 配送调度
    GET  /health         - 健康检查

启动:
    uvicorn app.main:app --host 0.0.0.0 --port 8001

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from fastapi import FastAPI

from app.core.fault import fault_injection_middleware
from app.routers import (
    delivery_router,
    order_router,
    poi_router,
    queue_router,
    route_router,
    weather_router,
)

app = FastAPI(
    title="SnapTrip Mock API",
    description="模拟美团本地生活 API：POI 搜索 / 排队 / 订座 / 下单 / 路线 / 天气 / 配送",
    version="0.2.0",
)

app.middleware("http")(fault_injection_middleware)

app.include_router(poi_router)
app.include_router(queue_router)
app.include_router(order_router)
app.include_router(route_router)
app.include_router(weather_router)
app.include_router(delivery_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
