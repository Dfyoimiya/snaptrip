"""外卖系统路由 —— 商家搜索/菜单/下单/状态追踪。

基于高德 POI ID 定位商家，菜单由模板引擎动态生成。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import math
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.schemas import ToolResult
from app.core.menu_templates import generate_menu

router = APIRouter(prefix="/takeout", tags=["takeout"])

_orders: dict[str, dict] = {}

# 外卖配送费基础参数
_DELIVERY_BASE_FEE = 5.0
_DELIVERY_PER_KM = 2.0


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/merchant/search")
async def search_merchants(
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    radius: float = Query(5.0),
    keyword: str = Query(""),
    cuisine: str = Query(""),
    limit: int = Query(20, le=30),
):
    """搜索外卖商家。

    实际场景中应调用高德周边搜索获取真实商家，
    这里模拟生成商家列表（用于独立测试）。
    """
    t0 = time.perf_counter()

    cuisines = ["火锅", "中餐", "日料", "西餐", "烧烤", "咖啡", "快餐", "烘焙"]
    if cuisine:
        cuisines = [c for c in cuisines if cuisine in c]

    merchants = []
    for i in range(min(limit, random.randint(8, 20))):
        dist = round(random.uniform(0.3, radius), 1)
        cuisine_name = random.choice(cuisines)
        merchants.append({
            "id": f"poi_tk_{uuid.uuid4().hex[:8]}",
            "name": f"{'★' if random.random() > 0.7 else ''}{cuisine_name}商家#{random.randint(100, 999)}",
            "cuisine": cuisine_name,
            "distance_km": dist,
            "avg_rating": round(random.uniform(3.5, 5.0), 1),
            "monthly_sales": random.randint(100, 9999),
            "delivery_fee": round(_DELIVERY_BASE_FEE + dist * _DELIVERY_PER_KM, 1),
            "min_order": random.choice([15, 20, 25, 30]),
            "delivery_time_min": 25 + int(dist * 5),
            "delivery_time_max": 40 + int(dist * 8),
            "tags": random.sample(["新店", "评分高", "送得快", "满减", "首单立减"], k=random.randint(1, 3)),
        })

    merchants.sort(key=lambda x: x["distance_km"])

    return ToolResult(
        status="success",
        data={"merchants": merchants, "total": len(merchants)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/merchant/{poi_id}/menu")
async def get_takeout_menu(
    poi_id: str,
    poi_type: str = Query("", description="高德 POI 类型"),
    poi_name: str = Query("", description="商家名称"),
):
    """获取外卖菜单。"""
    t0 = time.perf_counter()
    menu = generate_menu(poi_type=poi_type, poi_name=poi_name, is_takeout=True)
    menu["poi_id"] = poi_id

    # 外卖专属：满减优惠
    menu["promotions"] = random.choice([
        [{"type": "满减", "desc": "满30减5"}, {"type": "满减", "desc": "满50减10"}],
        [{"type": "满减", "desc": "满25减8"}, {"type": "满减", "desc": "满60减15"}],
        [{"type": "折扣", "desc": "全单8.8折"}, {"type": "满减", "desc": "满40减8"}],
    ])
    menu["packing_fee"] = round(random.uniform(1, 3), 1)

    return ToolResult(
        status="success",
        data=menu,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/prepare")
async def prepare_order(body: dict):
    """外卖预下单：计算价格、配送费、优惠。"""
    t0 = time.perf_counter()

    items = body.get("items", [])
    delivery_distance = body.get("delivery_distance_km", 2.0)

    # 计算商品金额
    item_total = 0.0
    prepared_items = []
    for it in items:
        price = round(random.uniform(8, 68), 1)
        qty = it.get("quantity", 1)
        subtotal = round(price * qty, 1)
        item_total += subtotal
        prepared_items.append({
            "menu_id": it.get("menu_id", f"mi_{uuid.uuid4().hex[:8]}"),
            "name": it.get("name", "商品"),
            "price": price,
            "quantity": qty,
            "subtotal": subtotal,
        })

    packing_fee = round(random.uniform(1, 3), 1)
    delivery_fee = round(_DELIVERY_BASE_FEE + delivery_distance * _DELIVERY_PER_KM, 1)

    # 满减优惠
    discount = 0.0
    promotions = []
    if item_total >= 60:
        discount = round(random.uniform(8, 15), 1)
        promotions.append({"type": "满减", "desc": f"满60减{discount:.0f}"})
    elif item_total >= 30:
        discount = round(random.uniform(3, 8), 1)
        promotions.append({"type": "满减", "desc": f"满30减{discount:.0f}"})

    total = round(item_total + packing_fee + delivery_fee - discount, 1)
    total = max(total, packing_fee + delivery_fee + 1)

    return ToolResult(
        status="success",
        data={
            "items": prepared_items,
            "item_total": round(item_total, 1),
            "packing_fee": packing_fee,
            "delivery_fee": delivery_fee,
            "delivery_distance_km": delivery_distance,
            "discount": round(discount, 1),
            "promotions": promotions,
            "total": total,
            "estimated_delivery_min": 25 + int(delivery_distance * 5),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/submit")
async def submit_order(body: dict):
    """提交外卖订单。"""
    t0 = time.perf_counter()

    if random.random() < 0.05:
        return ToolResult(
            status="failure",
            error_code="ORDER_SUBMIT_FAILED",
            error_message="订单提交失败，请重试",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order_id = f"tko_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    delivery_min = body.get("estimated_delivery_min", 35)

    order = {
        "order_id": order_id,
        "poi_id": body.get("poi_id", ""),
        "user_id": body.get("user_id", ""),
        "items": body.get("items", []),
        "total": body.get("total", 0),
        "status": "paid",
        "created_at": now.isoformat(),
        "estimated_delivery": (now + timedelta(minutes=delivery_min)).isoformat(),
        "delivery_address": body.get("address", ""),
        "remark": body.get("remark", ""),
        "rider": None,
        "status_timeline": [
            {"status": "paid", "time": now.isoformat(), "desc": "已支付"},
        ],
    }
    _orders[order_id] = order

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "status": "paid",
            "total": order["total"],
            "estimated_delivery": order["estimated_delivery"],
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/order/{order_id}")
async def get_order(order_id: str):
    """查询外卖订单详情（含骑手位置）。"""
    t0 = time.perf_counter()
    order = _orders.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    # 模拟状态推进
    _simulate_order_progress(order)

    return ToolResult(
        status="success",
        data=order,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/{order_id}/cancel")
async def cancel_order(order_id: str, body: dict = None):
    """取消外卖订单。"""
    t0 = time.perf_counter()
    order = _orders.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if order["status"] in ("delivering", "completed"):
        return ToolResult(
            status="failure",
            error_code="CANNOT_CANCEL",
            error_message=f"订单状态为 {order['status']}，无法取消",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order["status"] = "cancelled"
    order["status_timeline"].append({
        "status": "cancelled",
        "time": datetime.now(timezone.utc).isoformat(),
        "desc": (body or {}).get("reason", "用户取消"),
    })

    return ToolResult(
        status="success",
        data={"order_id": order_id, "status": "cancelled"},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


def _simulate_order_progress(order: dict):
    """根据时间推进订单状态 + 模拟骑手位置。"""
    now = datetime.now(timezone.utc)
    created = datetime.fromisoformat(order["created_at"])
    elapsed_sec = (now - created).total_seconds()

    # 骑手模拟：位置从商家 → 用户地址
    poi_lat, poi_lng = 39.91, 116.40  # 默认位置
    user_lat, user_lng = 39.92, 116.42  # 默认用户位置（约 2km）

    if elapsed_sec < 60 and order["status"] == "paid":
        order["status"] = "preparing"
        order["status_timeline"].append({"status": "preparing", "time": now.isoformat(), "desc": "商家备餐中"})
    elif 60 <= elapsed_sec < 180 and order["status"] == "preparing":
        order["status"] = "delivering"
        order["rider"] = {"name": f"骑手{random.choice('ABCD')}", "phone": f"138****{random.randint(1000, 9999)}", "rating": round(random.uniform(4.0, 5.0), 1)}
        order["status_timeline"].append({"status": "delivering", "time": now.isoformat(), "desc": "骑手已取餐，配送中"})

    if order["status"] == "delivering" and order["rider"]:
        # 骑手从商家位置移动到用户位置
        progress = min(1.0, (elapsed_sec - 180) / 900)  # 15分钟送达
        rider_lat = poi_lat + (user_lat - poi_lat) * progress + random.uniform(-0.002, 0.002)
        rider_lng = poi_lng + (user_lng - poi_lng) * progress + random.uniform(-0.002, 0.002)
        order["rider"]["lat"] = round(rider_lat, 6)
        order["rider"]["lng"] = round(rider_lng, 6)
        order["rider"]["distance_to_user_km"] = round(_haversine(rider_lat, rider_lng, user_lat, user_lng), 2)

    if elapsed_sec > 1200 and order["status"] == "delivering":
        order["status"] = "completed"
        order["status_timeline"].append({"status": "completed", "time": now.isoformat(), "desc": "已送达"})
