#!/usr/bin/env python3
"""根据商品实际内容调整价格并调用后端API更新。"""

import json
import requests
from statistics import mean
from typing import Any

# --- 配置 ---
BASE_URL = "http://localhost:8080/api/v1"
LOGIN_BODY = {"email": "admin@snaptrip.com", "password": "admin123"}
INPUT_FILE = "/Users/finley/01_Projects/Python_AI/snaptrip/products_for_pricing.json"

TARGET_CATEGORIES = {"食品酒饮", "粮油调味", "萌宠护理"}


# --- 价格判断规则 ---
def determine_price(name: str, category: str) -> tuple[float, float]:
    """
    根据商品名称和分类判断合理的市场价格（price）和原价（original_price）。
    返回 (price, original_price)
    """
    # -------- 食品酒饮 --------
    if category == "食品酒饮":
        if "劲酒" in name or "白酒" in name:
            # 劲牌 中国劲酒 35度 680ml*6瓶 整箱装
            if "680ml" in name and "6瓶" in name:
                price = 368.0
            elif "500ml" in name:
                price = 298.0
            else:
                price = 150.0
            original_price = round(price * 1.2, 2)
        elif "可口可乐" in name:
            if "迷你罐" in name or "200ml" in name:
                price = 35.0
            elif "12" in name:
                price = 35.0
            else:
                price = 45.0
            original_price = round(price * 1.3, 2)
        elif "哈根达斯" in name:
            if "473ml" in name:
                price = 89.0
            else:
                price = 79.0
            original_price = round(price * 1.3, 2)
        elif "喜之郎" in name or "果冻" in name:
            if "12杯" in name or "200克" in name:
                price = 48.0
            else:
                price = 28.0
            original_price = round(price * 1.4, 2)
        elif "思念" in name or "水饺" in name or "虾饺" in name:
            if "400g" in name:
                price = 38.0
            else:
                price = 32.0
            original_price = round(price * 1.3, 2)
        elif "蜂蜜水" in name or "蜂解" in name:
            if "6瓶" in name:
                price = 58.0
            else:
                price = 12.0
            original_price = round(price * 1.4, 2)
        elif "烤肠" in name or "锋味派" in name:
            if "175g" in name:
                price = 45.0
            else:
                price = 55.0
            original_price = round(price * 1.3, 2)
        else:
            price = 45.0
            original_price = round(price * 1.3, 2)

    # -------- 粮油调味 --------
    elif category == "粮油调味":
        if "KIRI" in name or "奶酪" in name or "小酪" in name:
            if "78g" in name:
                price = 32.0
            elif "128g" in name:
                price = 45.0
            else:
                price = 38.0
            original_price = round(price * 1.4, 2)
        elif "乐芝牛" in name:
            if "128g" in name and "2盒" in name:
                price = 42.0
            else:
                price = 28.0
            original_price = round(price * 1.4, 2)
        elif "大米" in name or "五常" in name or "稻花香" in name:
            if "10斤" in name or "5kg" in name:
                price = 65.0
            elif "5斤" in name:
                price = 38.0
            else:
                price = 55.0
            original_price = round(price * 1.3, 2)
        elif "螺蛳粉" in name or "好欢螺" in name:
            if "6袋" in name or "400克" in name:
                price = 68.0
            else:
                price = 55.0
            original_price = round(price * 1.3, 2)
        elif "胡姬花" in name or "花生油" in name or "食用油" in name:
            if "4L" in name:
                price = 98.0
            else:
                price = 75.0
            original_price = round(price * 1.2, 2)
        elif "龙稻" in name:
            if "5斤" in name:
                price = 35.0
            else:
                price = 55.0
            original_price = round(price * 1.3, 2)
        else:
            price = 50.0
            original_price = round(price * 1.3, 2)

    # -------- 萌宠护理 --------
    elif category == "萌宠护理":
        if "狗粮" in name or "猫粮" in name:
            if "12kg" in name:
                price = 289.0
            elif "5kg" in name or "10斤" in name:
                price = 168.0
            else:
                price = 128.0
            original_price = round(price * 1.25, 2)
        elif "猫罐头" in name or "罐头" in name:
            if "24罐" in name:
                price = 138.0
            elif "70g" in name:
                price = 6.5
            else:
                price = 88.0
            original_price = round(price * 1.3, 2)
        elif "猫砂" in name:
            if "10斤" in name:
                price = 28.0
            else:
                price = 22.0
            original_price = round(price * 1.4, 2)
        elif "驱虫" in name or "喷雾" in name:
            if "500ml" in name:
                price = 45.0
            else:
                price = 35.0
            original_price = round(price * 1.3, 2)
        elif "玩具" in name or "猫薄荷" in name or "用品" in name or "饮水器" in name or "喝水器" in name:
            price = 25.0
            original_price = round(price * 1.5, 2)
        else:
            price = 35.0
            original_price = round(price * 1.3, 2)

    else:
        price = 99.0
        original_price = 199.0

    price = round(price, 2)
    original_price = round(original_price, 2)
    return price, original_price


def get_token() -> str:
    """登录获取 admin token。"""
    resp = requests.post(f"{BASE_URL}/auth/login", json=LOGIN_BODY, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    assert data.get("code") == 0, f"登录失败: {data}"
    token = data["data"]["access_token"]
    print(f"[✓] 登录成功，获取 token")
    return token


def update_product(token: str, product_id: str, price: float, original_price: float) -> None:
    """更新商品价格和原价。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"price": price, "original_price": original_price}
    resp = requests.put(f"{BASE_URL}/admin/products/{product_id}", headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"更新商品 {product_id} 失败: {data}")


def get_product_detail(token: str, product_id: str) -> dict[str, Any]:
    """获取商品详情。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(f"{BASE_URL}/admin/products/{product_id}", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    assert data.get("code") == 0, f"获取商品详情失败: {data}"
    return data["data"]


def update_sku(token: str, product_id: str, sku_id: str, price: float, promotion_price: float) -> None:
    """更新 SKU 价格。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"price": price, "promotion_price": promotion_price}
    resp = requests.put(f"{BASE_URL}/admin/products/{product_id}/skus/{sku_id}", headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"更新 SKU {sku_id} 失败: {data}")


def main():
    # 1. 读取 JSON 文件
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    # 2. 筛选目标分类
    filtered = [p for p in products if p.get("category") in TARGET_CATEGORIES]
    print(f"[i] 共读取 {len(products)} 个商品，筛选出 {len(filtered)} 个目标商品\n")

    if not filtered:
        print("[!] 没有找到目标分类商品，退出")
        return

    # 3. 判断合理价格
    pricing_map: dict[str, tuple[float, float]] = {}
    for p in filtered:
        price, original_price = determine_price(p["name"], p["category"])
        pricing_map[p["id"]] = (price, original_price)

    # 4. 登录获取 token
    token = get_token()

    # 5. 逐个更新商品 + SKU
    print("\n" + "=" * 80)
    print("开始更新商品价格...")
    print("=" * 80)

    updated_records: list[dict[str, Any]] = []

    for p in filtered:
        pid = p["id"]
        name = p["name"]
        category = p["category"]
        old_price = p.get("price", 0.0)
        old_original = p.get("original_price", 0.0)
        new_price, new_original = pricing_map[pid]

        # 更新商品主价格
        update_product(token, pid, new_price, new_original)

        # 获取商品详情并更新 SKU
        detail = get_product_detail(token, pid)
        skus = detail.get("skus", []) or []
        for sku in skus:
            sku_id = sku.get("id")
            if sku_id:
                update_sku(token, pid, sku_id, new_price, new_original)

        sku_count = len(skus)
        record = {
            "id": pid,
            "name": name,
            "category": category,
            "old_price": old_price,
            "old_original_price": old_original,
            "new_price": new_price,
            "new_original_price": new_original,
            "sku_count": sku_count,
        }
        updated_records.append(record)
        print(f"[✓] {name[:40]:<40} | 分类: {category} | 价格: {old_price:.2f} → {new_price:.2f} | 原价: {old_original:.2f} → {new_original:.2f} | SKU: {sku_count}")

    # 6. 打印汇总
    print("\n" + "=" * 80)
    print("分类价格汇总")
    print("=" * 80)

    # 按分类分组统计
    from collections import defaultdict
    group = defaultdict(list)
    for r in updated_records:
        group[r["category"]].append(r["new_price"])

    for cat in sorted(group.keys()):
        prices = group[cat]
        print(f"\n分类: {cat}")
        print(f"  商品数量: {len(prices)}")
        print(f"  最高价格: {max(prices):.2f} 元")
        print(f"  最低价格: {min(prices):.2f} 元")
        print(f"  平均价格: {mean(prices):.2f} 元")

    print("\n" + "=" * 80)
    print("全部更新完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
