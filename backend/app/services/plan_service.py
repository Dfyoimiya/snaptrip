# mypy: ignore-errors
"""规划服务 —— 意图解析 + 两阶段规划算法"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from app.data.seed_pois import SEED_POIS
from app.schemas.plan import POI, PlanCreateRequest, PlanResponse, PlanSlot

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "重庆": (29.5630, 106.5516),
}

CITY_KEYWORDS = {
    "北京": ["北京", "朝阳", "海淀", "东城", "西城", "三里屯", "国贸", "簋街", "故宫",
              "长城", "天安门", "颐和园", "鸟巢", "王府井", "后海", "798"],
    "上海": ["上海", "浦东", "静安", "徐汇", "外滩", "新天地", "陆家嘴", "迪士尼",
              "南京路", "城隍庙", "武康路", "法租界"],
    "重庆": ["重庆", "渝中", "江北", "南岸", "洪崖洞", "解放碑", "磁器口", "南山",
              "火锅", "朝天门", "观音桥"],
}

TYPE_KEYWORDS = {
    "restaurant": ["吃", "饭", "餐厅", "火锅", "烤鸭", "川菜", "本帮菜", "聚餐", "晚饭", "午饭", "美食"],
    "cafe": ["咖啡", "下午茶", "奶茶", "猫咖", "喝茶", "甜点", "甜品"],
    "attraction": ["逛", "景点", "博物馆", "公园", "打卡", "拍照", "夜景", "古镇", "故宫"],
    "activity": ["玩", "运动", "骑行", "游乐", "乐园", "手工", "陶艺"],
}

MOOD_KEYWORDS = {
    "安静": ["安静", "清净", "放松", "休息"],
    "热闹": ["热闹", "嗨", "氛围好", "人气"],
    "浪漫": ["浪漫", "约会", "情侣"],
    "文艺": ["文艺", "小众", "艺术"],
    "亲子": ["带娃", "亲子", "小孩", "孩子"],
    "治愈": ["治愈", "温暖", "舒服"],
    "辣": ["辣", "麻辣", "重口味"],
    "拍照": ["拍照", "出片", "好看"],
}


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间距离 (km)"""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_intent(text: str) -> dict:
    """简单关键词意图解析"""
    result: dict = {
        "city": None,
        "type_prefs": [],
        "mood_prefs": [],
        "budget": None,
        "guest_count": 2,
    }

    for city, keywords in CITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            result["city"] = city
            break

    for ptype, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            result["type_prefs"].append(ptype)

    for mood, keywords in MOOD_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            result["mood_prefs"].append(mood)

    import re

    budget_match = re.search(r"预算(\d+)", text)
    if budget_match:
        result["budget"] = int(budget_match.group(1))
    else:
        price_match = re.search(r"人均(\d+)", text)
        if price_match:
            per_person = int(price_match.group(1))
            result["budget"] = per_person * 2

    count_match = re.search(r"(\d+)个?人", text)
    if count_match:
        result["guest_count"] = int(count_match.group(1))

    return result


def hard_filter(
    pois: list[POI], intent: dict, lat: float, lng: float,
    radius_km: float, start_time: datetime, end_time: datetime,
) -> list[POI]:
    """Phase 1: 硬约束过滤"""
    filtered: list[tuple[POI, int]] = []

    for poi in pois:
        score = 0

        if intent["city"] and poi.city != intent["city"]:
            continue
        score += 10

        dist = haversine(lat, lng, poi.lat, poi.lng)
        if intent["city"] and dist > radius_km:
            continue
        score += max(0, 10 - int(dist))

        if intent["type_prefs"] and poi.type not in intent["type_prefs"]:
            score -= 3

        if intent["budget"] and poi.avg_price > intent["budget"] * 0.7:
            score -= 2

        filtered.append((poi, score))

    filtered.sort(key=lambda x: -x[1])
    return [p for p, _ in filtered[:10]]


def soft_sort(pois: list[POI], intent: dict) -> list[POI]:
    """Phase 2: 软约束排序"""
    scored: list[tuple[POI, float]] = []

    for poi in pois:
        score = poi.rating * 2.0

        if intent["mood_prefs"]:
            mood_match = len(set(poi.mood_tags) & set(intent["mood_prefs"]))
            score += mood_match * 3.0

        if intent["type_prefs"] and poi.type in intent["type_prefs"]:
            score += 5.0

        if intent["budget"]:
            ratio = poi.avg_price / intent["budget"]
            if ratio < 0.5:
                score += 3.0
            elif ratio < 1.0:
                score += 1.0
            else:
                score -= 2.0

        scored.append((poi, score))

    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored]


def generate_slots(pois: list[POI], start_time: datetime, end_time: datetime) -> list[PlanSlot]:
    """根据 POI 列表生成时间轴 slots"""
    slots: list[PlanSlot] = []
    total_minutes = (end_time - start_time).total_seconds() / 60
    slot_count = min(len(pois), 4)
    slot_duration = total_minutes / max(slot_count, 1)
    current = start_time

    action_map = {
        "restaurant": "book_table",
        "cafe": "arrive",
        "attraction": "arrive",
        "activity": "book_ticket",
    }

    for i, poi in enumerate(pois[:slot_count]):
        move_time = random.randint(10, 25) if i > 0 else 0
        current += timedelta(minutes=move_time)

        slots.append(
            PlanSlot(
                sequence=i,
                time=current.strftime("%H:%M"),
                poi=poi,
                action=action_map.get(poi.type, "arrive"),
                estimated_cost=poi.avg_price,
                move_time_min=move_time,
            )
        )
        current += timedelta(minutes=min(slot_duration, 90))

        if current >= end_time:
            break

    return slots


async def create_plan(request: PlanCreateRequest) -> PlanResponse:
    """主流程：意图解析 → 过滤 → 排序 → 生成时隙"""
    intent = parse_intent(request.user_input)

    now = datetime.now()
    start_time = request.start_time or (now + timedelta(hours=1))
    end_time = request.end_time or (start_time + timedelta(hours=4))

    lat = request.lat
    lng = request.lng
    if intent["city"] and intent["city"] in CITY_CENTERS:
        lat, lng = CITY_CENTERS[intent["city"]]

    pois = [POI(**p.model_dump()) for p in SEED_POIS]

    candidates = hard_filter(pois, intent, lat, lng, radius_km=10.0, start_time=start_time, end_time=end_time)

    if not candidates:
        candidates = soft_sort(
            [p for p in pois if not intent["city"] or p.city == intent["city"]],
            intent,
        )[:3]

    ranked = soft_sort(candidates, intent)

    slots = generate_slots(ranked, start_time, end_time)

    total_cost = sum(s.estimated_cost for s in slots)
    total_time = sum(s.move_time_min for s in slots) + len(slots) * 60

    return PlanResponse(
        query_text=request.user_input,
        status="confirmed",
        total_cost=total_cost,
        total_time_min=total_time,
        slots=slots,
    )
