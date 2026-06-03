"""菜单模板引擎 —— 根据餐厅类型动态生成菜单。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import random
import uuid
from typing import Any

# =============================================================================
# 菜单模板定义：按 cuisine 类型组织
# =============================================================================

MENU_TEMPLATES: dict[str, dict[str, Any]] = {
    "hotpot": {
        "name": "火锅",
        "categories": [
            {
                "name": "锅底",
                "items": [
                    {"name": "麻辣红油锅底", "price_range": (38, 68), "is_specialty": True},
                    {"name": "番茄锅底", "price_range": (28, 48)},
                    {"name": "菌汤锅底", "price_range": (32, 52)},
                    {"name": "鸳鸯锅底", "price_range": (42, 72), "is_specialty": True},
                    {"name": "三鲜锅底", "price_range": (28, 45)},
                ],
            },
            {
                "name": "荤菜",
                "items": [
                    {"name": "极品肥牛", "price_range": (38, 68)},
                    {"name": "鲜切羊肉", "price_range": (42, 72)},
                    {"name": "毛肚", "price_range": (32, 58), "is_specialty": True},
                    {"name": "鸭肠", "price_range": (22, 38)},
                    {"name": "虾滑", "price_range": (28, 48)},
                    {"name": "牛百叶", "price_range": (30, 50)},
                    {"name": "鲜鸭血", "price_range": (15, 28)},
                    {"name": "午餐肉", "price_range": (18, 32)},
                ],
            },
            {
                "name": "素菜",
                "items": [
                    {"name": "土豆片", "price_range": (8, 15)},
                    {"name": "藕片", "price_range": (10, 18)},
                    {"name": "豆皮", "price_range": (8, 15)},
                    {"name": "金针菇", "price_range": (10, 18)},
                    {"name": "海带苗", "price_range": (8, 15)},
                    {"name": "冬瓜", "price_range": (6, 12)},
                ],
            },
            {
                "name": "小吃",
                "items": [
                    {"name": "红糖糍粑", "price_range": (15, 25)},
                    {"name": "酥肉", "price_range": (18, 30)},
                    {"name": "冰粉", "price_range": (8, 15)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "酸梅汤", "price_range": (8, 15)},
                    {"name": "王老吉", "price_range": (6, 10)},
                    {"name": "啤酒", "price_range": (8, 18)},
                ],
            },
        ],
    },
    "chinese": {
        "name": "中餐",
        "categories": [
            {
                "name": "凉菜",
                "items": [
                    {"name": "口水鸡", "price_range": (22, 38)},
                    {"name": "凉拌木耳", "price_range": (12, 22)},
                    {"name": "皮蛋豆腐", "price_range": (15, 25)},
                    {"name": "夫妻肺片", "price_range": (25, 42)},
                ],
            },
            {
                "name": "热菜",
                "items": [
                    {"name": "宫保鸡丁", "price_range": (28, 48), "is_specialty": True},
                    {"name": "鱼香肉丝", "price_range": (25, 42)},
                    {"name": "水煮鱼", "price_range": (48, 88), "is_specialty": True},
                    {"name": "回锅肉", "price_range": (28, 48)},
                    {"name": "麻婆豆腐", "price_range": (18, 32)},
                    {"name": "干煸四季豆", "price_range": (18, 30)},
                    {"name": "糖醋里脊", "price_range": (32, 52)},
                    {"name": "红烧排骨", "price_range": (38, 68)},
                ],
            },
            {
                "name": "主食",
                "items": [
                    {"name": "米饭", "price_range": (2, 5)},
                    {"name": "蛋炒饭", "price_range": (12, 22)},
                    {"name": "馒头", "price_range": (2, 5)},
                ],
            },
            {
                "name": "汤品",
                "items": [
                    {"name": "紫菜蛋花汤", "price_range": (12, 22)},
                    {"name": "酸辣汤", "price_range": (15, 25)},
                    {"name": "番茄蛋汤", "price_range": (10, 18)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "可乐", "price_range": (5, 10)},
                    {"name": "雪碧", "price_range": (5, 10)},
                    {"name": "椰汁", "price_range": (8, 15)},
                ],
            },
        ],
    },
    "japanese": {
        "name": "日料",
        "categories": [
            {
                "name": "刺身",
                "items": [
                    {"name": "三文鱼刺身", "price_range": (38, 68), "is_specialty": True},
                    {"name": "金枪鱼刺身", "price_range": (48, 88)},
                    {"name": "甜虾刺身", "price_range": (32, 58)},
                    {"name": "综合刺身拼盘", "price_range": (88, 168), "is_specialty": True},
                ],
            },
            {
                "name": "寿司",
                "items": [
                    {"name": "三文鱼寿司 (2贯)", "price_range": (15, 28)},
                    {"name": "鳗鱼寿司 (2贯)", "price_range": (18, 32)},
                    {"name": "加州卷 (8枚)", "price_range": (28, 48)},
                    {"name": "蟹籽军舰 (2贯)", "price_range": (12, 22)},
                ],
            },
            {
                "name": "烤物",
                "items": [
                    {"name": "烤鳗鱼", "price_range": (38, 68)},
                    {"name": "盐烤秋刀鱼", "price_range": (18, 32)},
                    {"name": "烤牛舌", "price_range": (28, 48)},
                ],
            },
            {
                "name": "炸物",
                "items": [
                    {"name": "天妇罗拼盘", "price_range": (35, 58)},
                    {"name": "炸猪排", "price_range": (28, 45)},
                    {"name": "炸鸡块", "price_range": (22, 35)},
                ],
            },
            {
                "name": "主食",
                "items": [
                    {"name": "豚骨拉面", "price_range": (32, 52)},
                    {"name": "牛肉饭", "price_range": (25, 42)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "清酒 (壶)", "price_range": (28, 58)},
                    {"name": "可尔必思", "price_range": (12, 20)},
                    {"name": "抹茶", "price_range": (15, 25)},
                ],
            },
        ],
    },
    "western": {
        "name": "西餐",
        "categories": [
            {
                "name": "前菜",
                "items": [
                    {"name": "凯撒沙拉", "price_range": (28, 48)},
                    {"name": "奶油蘑菇汤", "price_range": (22, 38)},
                    {"name": "法式焗蜗牛", "price_range": (48, 78)},
                ],
            },
            {
                "name": "主菜",
                "items": [
                    {"name": "菲力牛排", "price_range": (128, 258), "is_specialty": True},
                    {"name": "香煎三文鱼", "price_range": (68, 118)},
                    {"name": "烤春鸡", "price_range": (58, 98)},
                    {"name": "意式肉酱面", "price_range": (38, 68)},
                ],
            },
            {
                "name": "甜点",
                "items": [
                    {"name": "提拉米苏", "price_range": (28, 48)},
                    {"name": "巧克力熔岩蛋糕", "price_range": (32, 52)},
                    {"name": "焦糖布丁", "price_range": (18, 32)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "美式咖啡", "price_range": (18, 30)},
                    {"name": "拿铁", "price_range": (22, 35)},
                    {"name": "红葡萄酒 (杯)", "price_range": (38, 78)},
                ],
            },
        ],
    },
    "bbq": {
        "name": "烧烤",
        "categories": [
            {
                "name": "肉类",
                "items": [
                    {"name": "羊肉串 (10串)", "price_range": (25, 45)},
                    {"name": "牛肉串 (10串)", "price_range": (28, 48)},
                    {"name": "五花肉 (5串)", "price_range": (15, 28)},
                    {"name": "烤鸡翅 (4只)", "price_range": (18, 32)},
                    {"name": "烤羊排", "price_range": (38, 68), "is_specialty": True},
                ],
            },
            {
                "name": "海鲜",
                "items": [
                    {"name": "烤生蚝 (6只)", "price_range": (28, 48)},
                    {"name": "烤大虾 (6只)", "price_range": (32, 52)},
                    {"name": "烤鱿鱼", "price_range": (18, 32)},
                ],
            },
            {
                "name": "素菜",
                "items": [
                    {"name": "烤韭菜", "price_range": (8, 15)},
                    {"name": "烤茄子", "price_range": (10, 18)},
                    {"name": "烤馒头片", "price_range": (5, 10)},
                ],
            },
            {
                "name": "酒水",
                "items": [
                    {"name": "啤酒", "price_range": (8, 18)},
                    {"name": "扎啤 (1L)", "price_range": (18, 30)},
                    {"name": "可乐", "price_range": (5, 10)},
                ],
            },
        ],
    },
    "cafe": {
        "name": "咖啡/茶饮",
        "categories": [
            {
                "name": "意式咖啡",
                "items": [
                    {"name": "美式", "price_range": (18, 28)},
                    {"name": "拿铁", "price_range": (22, 35)},
                    {"name": "卡布奇诺", "price_range": (22, 35)},
                    {"name": "澳白", "price_range": (22, 32)},
                    {"name": "摩卡", "price_range": (25, 38)},
                ],
            },
            {
                "name": "手冲咖啡",
                "items": [
                    {"name": "耶加雪菲", "price_range": (28, 48)},
                    {"name": "曼特宁", "price_range": (28, 45)},
                ],
            },
            {
                "name": "茶饮",
                "items": [
                    {"name": "抹茶拿铁", "price_range": (22, 35)},
                    {"name": "伯爵红茶", "price_range": (18, 32)},
                    {"name": "水果茶", "price_range": (22, 38)},
                ],
            },
            {
                "name": "甜点",
                "items": [
                    {"name": "提拉米苏", "price_range": (25, 42)},
                    {"name": "芝士蛋糕", "price_range": (22, 38)},
                    {"name": "牛角包", "price_range": (12, 22)},
                ],
            },
        ],
    },
    "fast_food": {
        "name": "快餐",
        "categories": [
            {
                "name": "汉堡",
                "items": [
                    {"name": "经典汉堡", "price_range": (15, 28)},
                    {"name": "双层芝士汉堡", "price_range": (22, 38)},
                    {"name": "鸡腿汉堡", "price_range": (15, 28)},
                ],
            },
            {
                "name": "小食",
                "items": [
                    {"name": "薯条", "price_range": (8, 15)},
                    {"name": "鸡米花", "price_range": (10, 18)},
                    {"name": "鸡翅 (4只)", "price_range": (12, 22)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "可乐", "price_range": (5, 10)},
                    {"name": "橙汁", "price_range": (8, 15)},
                ],
            },
        ],
    },
    "bakery": {
        "name": "烘焙/甜品",
        "categories": [
            {
                "name": "面包",
                "items": [
                    {"name": "法式可颂", "price_range": (12, 22)},
                    {"name": "全麦吐司", "price_range": (15, 28)},
                    {"name": "蒜香法棍", "price_range": (8, 18)},
                ],
            },
            {
                "name": "蛋糕",
                "items": [
                    {"name": "黑森林", "price_range": (28, 48)},
                    {"name": "提拉米苏", "price_range": (25, 45)},
                    {"name": "芝士蛋糕", "price_range": (22, 38)},
                ],
            },
            {
                "name": "饮品",
                "items": [
                    {"name": "美式", "price_range": (16, 26)},
                    {"name": "拿铁", "price_range": (20, 32)},
                ],
            },
        ],
    },
}

# 默认模板（未知类型回退到中餐）
_DEFAULT_CUISINE = "chinese"

# 外卖价格系数（外卖通常比堂食便宜 10-20%）
_TAKEOUT_PRICE_FACTOR = 0.85


def _random_price(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 1)


def generate_menu(poi_type: str | None, poi_name: str = "", is_takeout: bool = False) -> dict:
    """根据餐厅类型动态生成菜单。

    Args:
        poi_type: 高德 POI 分类字符串, 如 "中餐厅;火锅"
        poi_name: POI 名称，用于生成推荐菜
        is_takeout: 是否为外卖菜单（价格略有差异）

    Returns:
        {"cuisine": "火锅", "categories": [...], "recommendations": [...]}
    """
    cuisine = _infer_cuisine(poi_type or "")
    template = MENU_TEMPLATES.get(cuisine, MENU_TEMPLATES[_DEFAULT_CUISINE])

    price_factor = _TAKEOUT_PRICE_FACTOR if is_takeout else 1.0

    categories = []
    all_items = []
    for cat in template["categories"]:
        cat_items = []
        for item in cat["items"]:
            price = _random_price(*item["price_range"])
            price = round(price * price_factor, 1)
            original_price = _random_price(*item["price_range"]) if is_takeout else 0.0
            menu_item = {
                "id": _make_item_id(),
                "name": item["name"],
                "price": price,
                "original_price": round(original_price, 1) if original_price else 0.0,
                "monthly_sales": random.randint(50, 3000),
                "rating": round(random.uniform(3.8, 5.0), 1),
                "is_specialty": item.get("is_specialty", False),
            }
            cat_items.append(menu_item)
            all_items.append(menu_item)
        categories.append({"name": cat["name"], "items": cat_items})

    # 选 3-5 个招牌菜作为推荐
    specialties = [i for i in all_items if i["is_specialty"]]
    if len(specialties) < 3:
        extras = [i for i in all_items if not i["is_specialty"]]
        specialties += random.sample(extras, min(3 - len(specialties), len(extras)))
    recommendations = [s["name"] for s in random.sample(specialties, min(5, len(specialties)))]

    return {
        "cuisine": template["name"],
        "poi_name": poi_name,
        "categories": categories,
        "recommendations": recommendations,
    }


def _infer_cuisine(poi_type: str) -> str:
    """从高德 POI 类型字符串推断 cuisine。"""
    t = poi_type.lower()
    if "火锅" in t:
        return "hotpot"
    if "日本" in t or "日料" in t or "寿司" in t or "刺身" in t:
        return "japanese"
    if "韩国" in t or "韩式" in t or "烤肉" in t:
        return "bbq"
    if "西餐" in t or "牛排" in t or "意大利" in t or "法国" in t:
        return "western"
    if "烧烤" in t or "烤串" in t or "烤肉" in t:
        return "bbq"
    if "咖啡" in t or "茶馆" in t or "茶饮" in t:
        return "cafe"
    if "快餐" in t or "小吃" in t:
        return "fast_food"
    if "面包" in t or "烘焙" in t or "蛋糕" in t or "甜品" in t:
        return "bakery"
    if "餐饮" in t or "餐厅" in t or "中餐" in t:
        return "chinese"
    return _DEFAULT_CUISINE


def _make_item_id() -> str:
    return f"mi_{uuid.uuid4().hex[:8]}"
