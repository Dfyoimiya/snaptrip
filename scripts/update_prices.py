#!/usr/bin/env python3
"""
商品定价调整脚本

流程：
1. 读取 products_for_pricing.json，筛选 "服饰鞋包" 和 "个人美妆"
2. 根据商品名称判断合理的市场价格
3. 调用后端 API 更新商品价格和 SKU 价格
4. 输出价格对比和分类汇总
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import requests

BASE_URL = "http://localhost:8080/api/v1"
LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"
PRODUCT_DETAIL_ENDPOINT = f"{BASE_URL}/admin/products/{{product_id}}"
PRODUCT_UPDATE_ENDPOINT = f"{BASE_URL}/admin/products/{{product_id}}"
SKU_UPDATE_ENDPOINT = f"{BASE_URL}/admin/products/{{product_id}}/skus/{{sku_id}}"

ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"


def login() -> str:
    """登录获取 admin access token."""
    resp = requests.post(
        LOGIN_ENDPOINT,
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"登录失败: {data}")
    return data["data"]["access_token"]


def get_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def load_products(path: str | Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_target_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_categories = {"服饰鞋包", "个人美妆"}
    return [p for p in products if p.get("category") in target_categories]


def determine_price(name: str, category: str) -> tuple[float, float]:
    """
    根据商品名称和分类判断合理的市场价格 (price, original_price)。
    original_price 设为 price 的 1.2~1.5 倍，模拟原价/折扣逻辑。
    """
    name_lower = name.lower()

    # ── 个人美妆 ──
    if category == "个人美妆":
        # 修容棒
        if "修容" in name or "修容棒" in name or "修容笔" in name:
            return (298.0, 368.0)
        # 素颜霜 / BB霜 / 隔离遮瑕
        if "素颜霜" in name or "bb霜" in name_lower or "遮瑕" in name or "防晒隔离" in name:
            return (168.0, 228.0)
        # 睫毛膏 / 睫毛打底
        if "睫毛膏" in name or "睫毛" in name:
            return (89.0, 139.0)
        # 牙线 / 牙签
        if "牙线" in name or "牙签" in name:
            return (19.9, 39.9)
        # 染发 / 染发霜 / 染发膏
        if "染发" in name:
            return (89.0, 129.0)
        # 润唇膏 / 唇蜜
        if "润唇膏" in name or "唇蜜" in name:
            return (298.0, 368.0)
        # 口红 / 口红礼盒
        if "口红" in name:
            return (398.0, 498.0)
        # 止汗喷雾 / 香体喷雾
        if "喷雾" in name and ("止汗" in name or "香体" in name or "腋下" in name):
            return (59.0, 89.0)
        # 遮瑕膏 / 遮瑕
        if "遮瑕" in name and "遮瑕膏" in name:
            return (290.0, 360.0)
        # 品牌名（仅品牌）兜底
        if name in ("施华蔻", "纪梵希", "茵芙莎", "舒耐"):
            return (128.0, 168.0)
        # 默认美妆
        return (128.0, 168.0)

    # ── 服饰鞋包 ──
    if category == "服饰鞋包":
        # 高跟鞋 / 凉鞋
        if "高跟鞋" in name or "凉鞋" in name or "高跟" in name:
            return (369.0, 499.0)
        # 托特包 / 单肩包 / 斜挎包 / 手提包 / 包包
        if "托特包" in name or "单肩包" in name or "斜挎包" in name or "手提包" in name or "包包" in name:
            return (198.0, 268.0)
        # 行李箱 / 拉杆箱 / 旅行箱
        if "行李箱" in name or "拉杆箱" in name or "旅行箱" in name:
            return (298.0, 398.0)
        # 手链 / 珠宝 / 施华洛世奇 / 黄金
        if "手链" in name or "珠宝" in name or "施华洛世奇" in name:
            if "黄金" in name:
                return (1580.0, 1980.0)
            return (458.0, 598.0)
        # 休闲鞋 / 运动鞋 / 板鞋 / 健步鞋
        if "鞋" in name and ("休闲" in name or "运动" in name or "板鞋" in name or "健步" in name):
            return (368.0, 468.0)
        # 睡衣 / 家居服
        if "睡衣" in name or "家居" in name:
            return (128.0, 168.0)
        # 眼镜 / 镜片 / 镜框
        if "眼镜" in name or "镜片" in name or "镜框" in name:
            return (568.0, 698.0)
        # POLO衫 / 短袖 / 服装
        if "polo衫" in name_lower or "短袖" in name or "t恤" in name_lower or "衫" in name:
            return (458.0, 598.0)
        # 品牌名（仅品牌）兜底
        if name in ("斯凯奇", "迪桑特", "蔡司", "老凤祥", "CHARLES&KEITH", "Lee", "MUJI"):
            return (328.0, 428.0)
        # 默认服饰鞋包
        return (198.0, 268.0)

    return (99.0, 199.0)


def update_product(token: str, product_id: str, price: float, original_price: float) -> dict[str, Any]:
    """更新商品基础价格。"""
    headers = get_auth_headers(token)
    resp = requests.put(
        PRODUCT_UPDATE_ENDPOINT.format(product_id=product_id),
        headers=headers,
        json={"price": price, "original_price": original_price},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"更新商品失败 [{product_id}]: {data}")
    return data["data"]


def get_product_detail(token: str, product_id: str) -> dict[str, Any]:
    """获取商品详情，包含 SKU 列表。"""
    headers = get_auth_headers(token)
    resp = requests.get(
        PRODUCT_DETAIL_ENDPOINT.format(product_id=product_id),
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取商品详情失败 [{product_id}]: {data}")
    return data["data"]


def update_sku(token: str, product_id: str, sku_id: str, price: float, promotion_price: float) -> dict[str, Any]:
    """更新单个 SKU 价格。"""
    headers = get_auth_headers(token)
    resp = requests.put(
        SKU_UPDATE_ENDPOINT.format(product_id=product_id, sku_id=sku_id),
        headers=headers,
        json={"price": price, "promotion_price": promotion_price},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"更新 SKU 失败 [{sku_id}]: {data}")
    return data["data"]


def main() -> None:
    json_path = Path("products_for_pricing.json")
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        return

    all_products = load_products(json_path)
    target_products = filter_target_products(all_products)

    print(f"📋 共读取 {len(all_products)} 个商品，筛选出 {len(target_products)} 个目标商品")
    print("=" * 80)

    # 登录
    token = login()
    print(f"✅ 登录成功，获取 admin token\n")

    # 记录调整信息
    adjustments: list[dict[str, Any]] = []

    for product in target_products:
        pid = product["id"]
        name = product["name"]
        category = product["category"]
        old_price = float(product["price"])
        old_original = float(product["original_price"])

        new_price, new_original = determine_price(name, category)

        # 更新商品基础价格
        try:
            update_product(token, pid, new_price, new_original)
        except Exception as e:
            print(f"❌ 商品更新失败 [{name}]: {e}")
            continue

        # 获取商品详情，更新 SKU 价格
        try:
            detail = get_product_detail(token, pid)
            skus = detail.get("skus", [])
            for sku in skus:
                sku_id = sku["id"]
                update_sku(token, pid, sku_id, new_price, new_price)
        except Exception as e:
            print(f"⚠️ SKU 更新失败 [{name}]: {e}")

        adjustments.append({
            "id": pid,
            "name": name,
            "category": category,
            "old_price": old_price,
            "old_original": old_original,
            "new_price": new_price,
            "new_original": new_original,
        })

        print(f"🛒 {name}")
        print(f"   分类: {category}")
        print(f"   价格: {old_price:.2f} → {new_price:.2f}")
        print(f"   原价: {old_original:.2f} → {new_original:.2f}")
        print()

    # 汇总输出
    print("=" * 80)
    print("📊 分类价格汇总")
    print("=" * 80)

    for category in ("个人美妆", "服饰鞋包"):
        cat_items = [a for a in adjustments if a["category"] == category]
        if not cat_items:
            continue

        prices = [a["new_price"] for a in cat_items]
        max_p = max(prices)
        min_p = min(prices)
        avg_p = statistics.mean(prices)

        print(f"\n【{category}】共 {len(cat_items)} 个商品")
        print(f"  最高价格: ¥{max_p:.2f}")
        print(f"  最低价格: ¥{min_p:.2f}")
        print(f"  平均价格: ¥{avg_p:.2f}")

    print("\n✅ 所有价格调整完成！")


if __name__ == "__main__":
    main()
