"""Mock API 服务入口 —— 模拟美团本地生活 API。

基于高德真实 POI 数据构建，覆盖:
  - 餐饮: 菜单 / 排队取号 / 餐厅预订
  - 外卖: 商家搜索 / 菜单 / 下单 / 骑手追踪
  - 电影: 影片 / 影院 / 场次 / 选座购票
  - 酒店: 搜索 / 房型 / 预订
  - 休闲: KTV / 密室 / 剧本杀 / 桌游 / 酒吧
  - 通用: 支付 / 订单查询 / 取消 / 退款
  - 已有: 配送 / 路线 / 天气

启动:
    uvicorn app.main:app --host 0.0.0.0 --port 8001

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

from fastapi import FastAPI

from app.core.fault import fault_injection_middleware
from app.routers import (
    delivery_router,
    hotel_router,
    leisure_router,
    movie_router,
    order_router,
    poi_router,
    reservation_router,
    route_router,
    takeout_router,
    weather_router,
)

app = FastAPI(
    title="SnapTrip Mock API",
    description="模拟美团本地生活 API：POI菜单/排队/预订/外卖/电影/酒店/休闲/订单/路线/天气/配送",
    version="0.3.0",
)

app.middleware("http")(fault_injection_middleware)

# ── 餐饮 ──
app.include_router(poi_router)          # /poi/{id}/menu, /poi/{id}/queue, /poi/{id}/queue/take
app.include_router(reservation_router)  # /reservation/{id}/slots, /reservation/create, /reservation/{id}/cancel

# ── 外卖 ──
app.include_router(takeout_router)      # /takeout/merchant/search, /takeout/merchant/{id}/menu, /takeout/order/*

# ── 电影 ──
app.include_router(movie_router)        # /movie/list, /cinema/search, /cinema/{id}/sessions, /session/{id}/seats, /movie/order/*

# ── 酒店 ──
app.include_router(hotel_router)        # /hotel/search, /hotel/{id}/rooms, /hotel/order/*

# ── 休闲 ──
app.include_router(leisure_router)      # /leisure/search, /leisure/{id}/slots, /leisure/booking/*

# ── 通用 ──
app.include_router(order_router)        # /order/prepare, /order/submit, /order/pay, /order/{id}, /order/{id}/cancel, /order/{id}/refund
app.include_router(delivery_router)     # /delivery/schedule

# ── 地理/天气（已有） ──
app.include_router(route_router)        # /route
app.include_router(weather_router)      # /weather


@app.get("/health")
async def health():
    return {"status": "ok"}
