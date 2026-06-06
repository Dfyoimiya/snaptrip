"""酒店住宿路由 —— 搜索/房型/预订。

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

from app.schemas import ToolResult, _make_id

router = APIRouter(prefix="/hotel", tags=["hotel"])

_orders: dict[str, dict] = {}

# 酒店品牌模板
_HOTEL_BRANDS = [
    {"name": "希尔顿", "star": 5, "base_price": 680},
    {"name": "万豪", "star": 5, "base_price": 750},
    {"name": "洲际", "star": 5, "base_price": 820},
    {"name": "凯悦", "star": 5, "base_price": 700},
    {"name": "华尔道夫", "star": 5, "base_price": 1200},
    {"name": "全季", "star": 3, "base_price": 280},
    {"name": "亚朵", "star": 4, "base_price": 380},
    {"name": "桔子", "star": 3, "base_price": 220},
    {"name": "如家精选", "star": 3, "base_price": 180},
    {"name": "汉庭优佳", "star": 3, "base_price": 200},
    {"name": "丽枫", "star": 4, "base_price": 320},
    {"name": "锦江之星", "star": 3, "base_price": 160},
    {"name": "威斯汀", "star": 5, "base_price": 880},
    {"name": "喜来登", "star": 5, "base_price": 650},
    {"name": "W酒店", "star": 5, "base_price": 950},
    {"name": "皇冠假日", "star": 5, "base_price": 600},
    {"name": "维也纳", "star": 4, "base_price": 300},
    {"name": "和颐", "star": 4, "base_price": 350},
    {"name": "开元名都", "star": 5, "base_price": 550},
    {"name": "书香门第", "star": 4, "base_price": 340},
]

# 北京/上海/重庆坐标参照
_CITY_COORDS = {
    "北京": (39.91, 116.40, [(39.90, 116.38), (39.93, 116.42), (39.95, 116.46),
                              (39.88, 116.44), (39.92, 116.48)]),
    "上海": (31.23, 121.47, [(31.22, 121.45), (31.24, 121.49), (31.20, 121.43),
                              (31.25, 121.50), (31.21, 121.47)]),
    "重庆": (29.56, 106.55, [(29.55, 106.53), (29.57, 106.57), (29.54, 106.56),
                              (29.58, 106.54), (29.55, 106.58)]),
}


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/search")
async def search_hotels(
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    radius: float = Query(10.0),
    city: str = Query("北京"),
    star_min: int = Query(0, description="最低星级"),
    star_max: int = Query(5, description="最高星级"),
    keyword: str = Query(""),
    limit: int = Query(20, le=30),
):
    """搜索酒店。"""
    t0 = time.perf_counter()

    # 获取城市坐标
    coords_list = _CITY_COORDS.get(city, _CITY_COORDS["北京"])[2]

    hotels = []
    # 为城市生成酒店
    brand_pool = [b for b in _HOTEL_BRANDS if star_min <= b["star"] <= star_max]
    if keyword:
        brand_pool = [b for b in brand_pool if keyword in b["name"]]

    for i, brand in enumerate(brand_pool[:limit]):
        base_coord = coords_list[i % len(coords_list)]
        flat = base_coord[0] + random.uniform(-0.015, 0.015)
        flng = base_coord[1] + random.uniform(-0.015, 0.015)
        dist = _haversine(lat, lng, flat, flng)
        if dist > radius:
            continue

        hotels.append({
            "id": f"htl_{uuid.uuid4().hex[:8]}",
            "name": f"{brand['name']}{city}{random.choice(['中心', '广场', '国际', '旗舰'])}店",
            "brand": brand["name"],
            "city": city,
            "lat": round(flat, 6),
            "lng": round(flng, 6),
            "star_level": brand["star"],
            "avg_rating": round(random.uniform(3.8, 5.0), 1),
            "distance_km": round(dist, 1),
            "address": f"{city}市{'朝阳区' if city == '北京' else '徐汇区' if city == '上海' else '渝中区'}XX路{random.randint(10, 999)}号",
            "base_price": brand["base_price"],
            "tags": random.sample(["商务", "亲子", "浪漫", "设计感", "海景", "市中心", "交通便利", "健身房", "游泳池"], k=random.randint(2, 4)),
            "facilities": random.sample(["WiFi", "停车场", "游泳池", "健身房", "餐厅", "SPA", "会议室", "儿童乐园"], k=random.randint(3, 6)),
        })

    hotels.sort(key=lambda x: x["distance_km"])
    return ToolResult(
        status="success",
        data={"hotels": hotels, "total": len(hotels)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/{hotel_id}/rooms")
async def get_hotel_rooms(
    hotel_id: str,
    check_in: str = Query("", description="入住日期"),
    check_out: str = Query("", description="离店日期"),
):
    """房型列表。"""
    t0 = time.perf_counter()

    # 从 hotel_id 推断星级
    star_level = 3
    room_templates = _get_room_templates(star_level)

    rooms = []
    for tmpl in room_templates:
        price = round(tmpl["base_price"] * random.uniform(0.85, 1.15), 1)
        rooms.append({
            "id": _make_id("rm"),
            "hotel_id": hotel_id,
            "name": tmpl["name"],
            "bed_type": tmpl["bed_type"],
            "area_m2": tmpl["area_m2"],
            "max_guests": tmpl["max_guests"],
            "price": price,
            "breakfast": tmpl["breakfast"],
            "cancel_policy": tmpl["cancel_policy"],
            "available_rooms": random.randint(0, 8),
            "amenities": tmpl["amenities"],
            "window": random.choice(["有窗", "有窗", "无窗"]),
        })

    return ToolResult(
        status="success",
        data={
            "hotel_id": hotel_id,
            "check_in": check_in,
            "check_out": check_out,
            "rooms": rooms,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/prepare")
async def prepare_hotel_order(body: dict):
    """酒店下单准备。"""
    t0 = time.perf_counter()
    room_count = body.get("room_count", 1)
    nights = body.get("nights", 1)
    price_per_night = body.get("price_per_night", 300)

    subtotal = round(price_per_night * nights * room_count, 1)
    service_fee = round(subtotal * 0.05, 1)
    total = round(subtotal + service_fee, 1)

    return ToolResult(
        status="success",
        data={
            "hotel_id": body.get("hotel_id", ""),
            "room_id": body.get("room_id", ""),
            "room_count": room_count,
            "nights": nights,
            "price_per_night": price_per_night,
            "subtotal": subtotal,
            "service_fee": service_fee,
            "total": total,
            "check_in": body.get("check_in", ""),
            "check_out": body.get("check_out", ""),
            "cancel_policy": "入住当日18:00前免费取消",
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/submit")
async def submit_hotel_order(body: dict):
    """提交酒店订单。"""
    t0 = time.perf_counter()

    if random.random() < 0.05:
        return ToolResult(
            status="failure",
            error_code="ORDER_FAILED",
            error_message="下单失败，房间可能已被抢订",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order_id = _make_id("htl")
    order = {
        "order_id": order_id,
        "hotel_id": body.get("hotel_id", ""),
        "room_id": body.get("room_id", ""),
        "total": body.get("total", 0),
        "status": "confirmed",
        "check_in": body.get("check_in", ""),
        "check_out": body.get("check_out", ""),
        "confirm_no": f"CF{random.randint(100000, 999999)}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _orders[order_id] = order

    return ToolResult(
        status="success",
        data=order,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/order/{order_id}/cancel")
async def cancel_hotel_order(order_id: str, body: dict = None):
    """取消酒店订单。"""
    t0 = time.perf_counter()
    order = _orders.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order["status"] = "cancelled"
    return ToolResult(
        status="success",
        data={"order_id": order_id, "status": "cancelled"},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


def _get_room_templates(star: int) -> list[dict]:
    if star >= 5:
        return [
            {"name": "豪华大床房", "bed_type": "大床", "area_m2": 42, "max_guests": 2,
             "base_price": 800, "breakfast": True, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["浴缸", "迷你吧", "智能马桶", "胶囊咖啡机"]},
            {"name": "行政双床房", "bed_type": "双床", "area_m2": 45, "max_guests": 2,
             "base_price": 880, "breakfast": True, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["行政酒廊", "浴缸", "迷你吧"]},
            {"name": "行政套房", "bed_type": "大床", "area_m2": 72, "max_guests": 3,
             "base_price": 1500, "breakfast": True, "cancel_policy": "入住前24小时免费取消",
             "amenities": ["客厅", "行政酒廊", "浴缸", "管家服务"]},
            {"name": "总统套房", "bed_type": "大床", "area_m2": 150, "max_guests": 4,
             "base_price": 5000, "breakfast": True, "cancel_policy": "不可取消",
             "amenities": ["客厅", "餐厅", "私人管家", "按摩浴缸", "钢琴"]},
        ]
    elif star >= 4:
        return [
            {"name": "标准大床房", "bed_type": "大床", "area_m2": 28, "max_guests": 2,
             "base_price": 350, "breakfast": False, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi", "智能电视"]},
            {"name": "商务双床房", "bed_type": "双床", "area_m2": 32, "max_guests": 2,
             "base_price": 380, "breakfast": True, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi", "智能电视", "办公桌"]},
            {"name": "豪华大床房", "bed_type": "大床", "area_m2": 35, "max_guests": 2,
             "base_price": 420, "breakfast": True, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi", "智能电视", "迷你吧", "浴袍"]},
            {"name": "家庭房", "bed_type": "大床+单人", "area_m2": 42, "max_guests": 3,
             "base_price": 480, "breakfast": True, "cancel_policy": "入住前24小时免费取消",
             "amenities": ["WiFi", "儿童用品", "浴缸"]},
        ]
    else:
        return [
            {"name": "大床房", "bed_type": "大床", "area_m2": 20, "max_guests": 2,
             "base_price": 180, "breakfast": False, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi"]},
            {"name": "双床房", "bed_type": "双床", "area_m2": 22, "max_guests": 2,
             "base_price": 200, "breakfast": False, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi"]},
            {"name": "商务大床房", "bed_type": "大床", "area_m2": 25, "max_guests": 2,
             "base_price": 230, "breakfast": True, "cancel_policy": "入住当日18:00前免费取消",
             "amenities": ["WiFi", "办公桌"]},
        ]
