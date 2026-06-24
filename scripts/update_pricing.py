#!/usr/bin/env python3
"""根据商品实际内容调整价格并调用后端API更新。"""

import json
import os
import requests
import sys
import time
from statistics import mean
from typing import Any

# --- 配置 ---
BASE_URL = "http://localhost:8080/api/v1"
LOGIN_BODY = {"email": "admin@snaptrip.com", "password": "admin123"}
INPUT_FILE = "/Users/finley/01_Projects/Python_AI/snaptrip/products_for_pricing.json"

TARGET_CATEGORIES = {"数码产品", "家用电器"}


def get_token() -> str:
    """登录获取 admin token，支持重试。"""
    for attempt in range(5):
        resp = requests.post(f"{BASE_URL}/auth/login", json=LOGIN_BODY, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            print("[✓] 登录成功，获取 token")
            return data["data"]["access_token"]
        if resp.status_code == 429:
            wait = 2 ** attempt
            print(f"[!] 登录限流 (429)，等待 {wait}s 后重试...")
            time.sleep(wait)
        else:
            resp.raise_for_status()
            raise RuntimeError(f"登录失败: {data}")
    raise RuntimeError("登录多次失败，请稍后再试")


# --- 价格判断规则 ---
def determine_price(name: str, category: str) -> tuple[float, float]:
    """
    根据商品名称和分类判断合理的市场价格（price）和原价（original_price）。
    返回 (price, original_price)
    """
    name_lower = name.lower()

    # 1. 手机 / 笔记本（排除"笔记本台式机"等配件描述）
    if any(k in name for k in ["手机", "游戏本", "笔记本电脑", "iPhone", "MacBook", "MateBook", "荣耀笔记本", "方正笔记本"]):
        if "荣耀" in name or "方正" in name or "x14" in name_lower:
            price = 3999.0
        elif "机械革命" in name or "极光" in name:
            price = 6999.0
        elif "小米" in name and "15" in name:
            price = 4499.0
        elif "hanuwei" in name_lower or "骁龙" in name:
            price = 3299.0
        else:
            price = 4999.0
        return price, round(price * 1.15, 2)

    # 2. 平板电脑 / 智能手表 / 穿戴设备
    if any(k in name for k in ["平板", "iPad", "手表", "Watch", "手环", "穿戴"]):
        if "redmi" in name_lower or "红米" in name:
            price = 799.0
        elif "apple" in name_lower or "苹果" in name:
            price = 2999.0
        else:
            price = 1599.0
        return price, round(price * 1.15, 2)

    # 3. 耳机 / 音响 / 音箱
    if any(k in name for k in ["耳机", "音响", "音箱", "earphone", "headphone", "speaker", "soundbar", "sound bar"]):
        if "soundbar" in name_lower or "桌面" in name:
            price = 599.0
        elif "airpods" in name_lower or "索尼" in name:
            price = 1899.0
        else:
            price = 399.0
        return price, round(price * 1.15, 2)

    # 4. 鼠标 / 键盘 / 外设
    if any(k in name for k in ["鼠标", "键盘", "mouse", "keyboard", "gpw"]):
        if "gpw" in name_lower or "狗屁王" in name or "罗技" in name:
            price = 899.0
        else:
            price = 299.0
        return price, round(price * 1.15, 2)

    # 5. 播放器 / 机顶盒 / 家庭影院（必须在硬盘之前，避免"硬盘播放器"被误判）
    if any(k in name for k in ["播放器", "机顶盒", "影院", "蓝光", "ZIDOO", "芝杜"]):
        price = 2199.0
        return price, round(price * 1.15, 2)

    # 6. 运动相机 / 相机 / 无人机
    if any(k in name for k in ["相机", "无人机", "Osmo", "GoPro", "大疆", "摄像机", "摄影"]):
        if "nano" in name_lower or "运动" in name:
            price = 1699.0
        elif "action" in name_lower:
            price = 2199.0
        else:
            price = 2499.0
        return price, round(price * 1.15, 2)

    # 7. 游戏机 / 掌机
    if any(k in name for k in ["Switch", "任天堂", "游戏机", "掌机", "PS5", "Xbox"]):
        if "switch2" in name_lower or "switch 2" in name_lower:
            price = 3299.0
        elif "switch" in name_lower or "oled" in name_lower:
            price = 2199.0
        else:
            price = 2599.0
        return price, round(price * 1.15, 2)

    # 8. 硬盘 / 内存 / SSD / 存储
    if any(k in name for k in ["硬盘", "内存", "SSD", "固态", "U盘", "存储", "SN7100"]):
        if "1TB" in name or "1t" in name_lower:
            price = 599.0
        elif "2TB" in name or "2t" in name_lower:
            price = 999.0
        elif "512" in name or "500" in name:
            price = 399.0
        else:
            price = 499.0
        return price, round(price * 1.15, 2)

    # 9. 空调 / 冰箱（大电器）
    if any(k in name for k in ["空调", "冰箱", "冷柜", "制冰"]):
        if "1.5匹" in name or "壁挂" in name:
            price = 2499.0
        elif "505L" in name or "十字门" in name or "双系统" in name:
            price = 4299.0
        else:
            price = 3499.0
        return price, round(price * 1.15, 2)

    # 10. 电视支架 / 配件（必须在"洗衣机/电视"之前，避免"电视支架"被误判为电视）
    if any(k in name for k in ["支架", "移动支架", "电视架", "落地"]):
        if "65" in name or "100" in name:
            price = 499.0
        else:
            price = 299.0
        return price, round(price * 1.15, 2)

    # 11. 洗衣机 / 电视 / 烘干机
    if any(k in name for k in ["洗衣机", "电视", "烘干机", "洗烘", "壁挂"]):
        if "内衣" in name or "壁挂" in name or "小型" in name:
            price = 1899.0
        elif "65" in name or "100" in name:
            price = 3999.0
        else:
            price = 2999.0
        return price, round(price * 1.15, 2)

    # 12. 小家电（温湿度计、空气净化器、扫地机等）
    if any(k in name for k in ["温湿度计", "净化器", "扫地机", "加湿器", "电吹风", "吹风机", "电饭煲", "微波炉"]):
        if "米家" in name or "小米" in name:
            price = 49.0
        else:
            price = 299.0
        return price, round(price * 1.15, 2)

    # 兜底：根据分类给一个默认值
    if category == "数码产品":
        price = 1999.0
    elif category == "家用电器":
        price = 2999.0
    else:
        price = 99.0
    return price, round(price * 1.15, 2)


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

    # 4. 登录获取 token（支持环境变量 ADMIN_TOKEN 以避免重复登录）
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        token = get_token()
    else:
        print("[✓] 使用环境变量 ADMIN_TOKEN")

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
                promotion = round(new_price * 0.9, 2)
                update_sku(token, pid, sku_id, new_price, promotion)

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
