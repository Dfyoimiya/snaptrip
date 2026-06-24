#!/usr/bin/env python3
"""用户活动数据导入脚本 —— 主控脚本。

功能:
    1. 创建 N 个用户并保存 token
    2. 获取所有商品信息
    3. 为每个用户添加随机购物车商品
    4. 将商品分组保存到文件
    5. 启动 worker 子进程并行导入订单和评论

用法:
    python import_user_activity.py [--users 25] [--reviews-per-product 20] [--orders-per-product 5]

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"

WORK_DIR = Path("/Users/finley/01_Projects/Python_AI/snaptrip/.import_work")


# ── 评论内容模板 ──
REVIEW_TEMPLATES = [
    "商品质量很好，物流速度也很快，非常满意！",
    "性价比很高，推荐购买。",
    "包装精美，实物与描述一致。",
    "使用了一段时间，感觉不错。",
    "客服态度很好，解决问题很及时。",
    "商品稍微有点瑕疵，但总体还可以接受。",
    "非常超出预期，会回购！",
    "价格实惠，质量也没得说。",
    "物流有点慢，但商品本身不错。",
    "完全满足我的需求，好评！",
    "做工精致，用料扎实。",
    "家人都很喜欢，下次还会来。",
    "比想象中还要好，必须五星好评！",
    "功能齐全，操作简单。",
    "外观漂亮，放在家里很上档次。",
    "用了几天感觉稳定性很好。",
    "商品质量不错，但价格偏贵。",
    "非常实用，解决了很多问题。",
    "包装很用心，没有任何损坏。",
    "效果立竿见影，强烈推荐！",
    "材质很好，摸起来手感舒适。",
    "设计很人性化，细节到位。",
    "发货速度超快，第二天就到了。",
    "和图片描述一致，没有色差。",
    "整体满意，会推荐给朋友。",
    "这是第二次购买了，品质如一。",
    "性价比之王，闭眼入。",
    "大小合适，非常贴合需求。",
    "质量很好，没有异味。",
    "安装简单，说明书很清晰。",
]


def _api_call(method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 15) -> dict:
    """使用 urllib 发起 HTTP 请求。"""
    req_headers = headers.copy() if headers else {}
    req_headers.setdefault("Content-Type", "application/json")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            error_body = {"message": str(exc)}
        raise RuntimeError(f"HTTP {exc.code}: {error_body}")


def login(email: str, password: str, base_url: str = BASE_URL) -> str:
    """登录获取 access_token。"""
    url = f"{base_url}{API_PREFIX}/auth/login"
    data = _api_call("POST", url, {"email": email, "password": password})
    if data.get("code") != 0:
        raise RuntimeError(f"登录失败 [{email}]: {data.get('message')}")
    return data["data"]["access_token"]


def register_user(email: str, password: str, base_url: str = BASE_URL) -> str:
    """注册用户并返回 token。"""
    url = f"{base_url}{API_PREFIX}/auth/register"
    data = _api_call("POST", url, {"email": email, "password": password})
    if data.get("code") != 0:
        # 可能已注册，尝试登录
        return login(email, password, base_url)
    return data["data"]["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_users(count: int, base_url: str = BASE_URL) -> list[dict[str, str]]:
    """创建多个用户，返回 [{email, token}] 列表。"""
    users = []
    for i in range(1, count + 1):
        email = f"user_{i:03d}@example.com"
        password = "test123456"
        success = False
        retries = 0
        max_retries = 5
        while not success and retries < max_retries:
            try:
                token = register_user(email, password, base_url)
                users.append({"email": email, "token": token, "user_id": None})
                print(f"  [用户 {i}/{count}] ✓ {email}")
                success = True
            except RuntimeError as exc:
                if "429" in str(exc):
                    wait = 5 + retries * 5
                    print(f"  [用户 {i}/{count}] 429，等待 {wait}s 后重试...")
                    time.sleep(wait)
                    retries += 1
                else:
                    print(f"  [用户 {i}/{count}] ✗ {email}: {exc}")
                    break
            except Exception as exc:
                print(f"  [用户 {i}/{count}] ✗ {email}: {exc}")
                break
        if not success:
            print(f"  [用户 {i}/{count}] ✗ {email}: 最终失败")
        time.sleep(2)
    return users


def get_all_products(base_url: str = BASE_URL, admin_token: str = "") -> list[dict]:
    """获取所有商品信息。"""
    # 获取所有商品（分页，每页100）
    all_items = []
    page = 1
    while True:
        url = f"{base_url}{API_PREFIX}/admin/products?page={page}&page_size=100"
        data = _api_call("GET", url, headers=_h(admin_token))
        if data.get("code") != 0:
            raise RuntimeError(f"获取商品失败: {data.get('message')}")
        items = data["data"]["items"]
        all_items.extend(items)
        if len(items) < 100:
            break
        page += 1
    # 提取关键字段
    products = []
    for item in all_items:
        products.append({
            "id": item["id"],
            "name": item["name"],
            "price": str(item["price"]),
            "default_pic": item.get("default_pic", ""),
            "category_id": item.get("category_id", ""),
            "category_name": item.get("category_name", ""),
        })
    return products


def get_product_skus(product_id: str, base_url: str = BASE_URL, admin_token: str = "") -> list[dict]:
    """获取商品 SKU 列表。"""
    url = f"{base_url}{API_PREFIX}/admin/products/{product_id}"
    data = _api_call("GET", url, headers=_h(admin_token))
    if data.get("code") != 0:
        return []
    skus = data["data"].get("skus", [])
    return skus


def add_to_cart(user_token: str, product_id: str, sku_id: str, quantity: int, base_url: str = BASE_URL) -> bool:
    """添加商品到购物车。"""
    url = f"{base_url}{API_PREFIX}/portal/cart"
    payload = {
        "product_id": product_id,
        "sku_id": sku_id,
        "quantity": quantity,
    }
    try:
        data = _api_call("POST", url, payload, _h(user_token))
        return data.get("code") == 0
    except Exception as exc:
        print(f"    购物车添加失败: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="导入用户活动数据")
    parser.add_argument("--users", type=int, default=25, help="创建用户数量")
    parser.add_argument("--reviews-per-product", type=int, default=20, help="每个商品评论数")
    parser.add_argument("--orders-per-product", type=int, default=5, help="每个商品订单数")
    parser.add_argument("--base-url", type=str, default=BASE_URL, help="后端基础URL")
    parser.add_argument("--workers", type=int, default=5, help="并行worker数量")
    args = parser.parse_args()

    WORK_DIR.mkdir(exist_ok=True)

    print(f"{'='*60}")
    print("用户活动数据导入 —— 主控脚本")
    print(f"{'='*60}")
    print(f"  用户数量: {args.users}")
    print(f"  每个商品评论数: {args.reviews_per_product}")
    print(f"  每个商品订单数: {args.orders_per_product}")
    print(f"  Worker 数量: {args.workers}")
    print(f"  后端URL: {args.base_url}")
    print()

    # 1. 获取 admin token
    print("[1/5] 获取 admin token...")
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD, args.base_url)
    print("  ✓ 登录成功\n")

    # 2. 创建用户
    print(f"[2/5] 创建 {args.users} 个用户...")
    users = create_users(args.users, args.base_url)
    with open(WORK_DIR / "users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 成功创建 {len(users)} 个用户\n")

    # 3. 获取所有商品
    print("[3/5] 获取所有商品信息...")
    products = get_all_products(args.base_url, admin_token)
    # 为每个商品获取 SKU
    for p in products:
        skus = get_product_skus(p["id"], args.base_url, admin_token)
        if skus:
            p["sku_id"] = skus[0]["id"]
            p["sku_price"] = str(skus[0]["price"])
        else:
            p["sku_id"] = None
            p["sku_price"] = p["price"]
    # 过滤掉没有 SKU 的商品
    products = [p for p in products if p.get("sku_id")]
    with open(WORK_DIR / "products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 获取 {len(products)} 个商品（含SKU）\n")

    # 4. 为每个用户添加购物车商品
    print("[4/5] 为每个用户添加购物车商品...")
    cart_count = 0
    random.seed(42)
    for user in users:
        # 随机选 5-8 个商品
        num_items = random.randint(5, 8)
        selected = random.sample(products, min(num_items, len(products)))
        for p in selected:
            if add_to_cart(user["token"], p["id"], p["sku_id"], random.randint(1, 3), args.base_url):
                cart_count += 1
                time.sleep(0.1)
        print(f"  {user['email']}: 添加了 {num_items} 个购物车商品")
    print(f"  ✓ 总共添加 {cart_count} 个购物车条目\n")

    # 5. 将商品分组，保存为 worker 任务文件
    print(f"[5/5] 分配任务给 {args.workers} 个 worker...")
    chunk_size = (len(products) + args.workers - 1) // args.workers
    chunks = [products[i:i+chunk_size] for i in range(0, len(products), chunk_size)]
    for i, chunk in enumerate(chunks):
        task_file = WORK_DIR / f"task_{i}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump({
                "worker_id": i,
                "products": chunk,
                "users": users,
                "admin_token": admin_token,
                "base_url": args.base_url,
                "reviews_per_product": args.reviews_per_product,
                "orders_per_product": args.orders_per_product,
            }, f, ensure_ascii=False, indent=2)
        print(f"  Worker {i}: {len(chunk)} 个商品 -> {task_file}")

    print(f"\n{'='*60}")
    print("主控脚本完成。请运行以下命令启动 workers:")
    print(f"{'='*60}")
    for i in range(len(chunks)):
        print(f"  python import_user_activity_worker.py --task {i}")
    print()
    print(f"或使用并行执行（{len(chunks)} 个窗口）:")
    for i in range(len(chunks)):
        print(f"  python import_user_activity_worker.py --task {i} &")
    print("  wait")
    print(f"\n工作目录: {WORK_DIR}")


if __name__ == "__main__":
    main()
