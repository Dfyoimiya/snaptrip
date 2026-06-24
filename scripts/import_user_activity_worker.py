#!/usr/bin/env python3
"""用户活动数据导入脚本 —— Worker 子进程。

功能:
    读取任务文件，为分配的商品创建订单和评论。

用法:
    python import_user_activity_worker.py --task 0

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WORK_DIR = Path("/Users/finley/01_Projects/Python_AI/snaptrip/.import_work")

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


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_order_direct(user_token: str, product_id: str, sku_id: str, quantity: int, price: str, base_url: str) -> dict | None:
    """直接购买创建订单。"""
    url = f"{base_url}/api/v1/portal/orders"
    payload = {
        "product_id": product_id,
        "sku_id": sku_id,
        "quantity": quantity,
        "receiver_name": "测试用户",
        "receiver_phone": "13800138000",
        "receiver_province": "测试省",
        "receiver_city": "测试市",
        "receiver_region": "测试区",
        "receiver_detail_address": "测试地址 123 号",
        "receiver_post_code": "518000",
        "pay_type": 1,
    }
    try:
        data = _api_call("POST", url, payload, _h(user_token), timeout=15)
        if data.get("code") == 0:
            return data["data"]
        else:
            print(f"      创建订单失败: {data.get('message')}")
            return None
    except Exception as exc:
        print(f"      创建订单异常: {exc}")
        return None


def pay_order(user_token: str, order_id: str, base_url: str) -> bool:
    """支付订单。"""
    url = f"{base_url}/api/v1/portal/orders/{order_id}/pay"
    try:
        data = _api_call("POST", url, headers=_h(user_token), timeout=10)
        return data.get("code") == 0
    except Exception as exc:
        print(f"      支付失败: {exc}")
        return False


def deliver_order(admin_token: str, order_id: str, base_url: str) -> bool:
    """Admin 发货。"""
    url = f"{base_url}/api/v1/admin/orders/{order_id}/delivery"
    payload = {
        "delivery_company": "顺丰速运",
        "delivery_sn": f"SF{random.randint(1000000000, 9999999999)}",
    }
    try:
        data = _api_call("POST", url, payload, _h(admin_token), timeout=10)
        return data.get("code") == 0
    except Exception as exc:
        print(f"      发货失败: {exc}")
        return False


def confirm_receipt(user_token: str, order_id: str, base_url: str) -> bool:
    """用户确认收货。"""
    url = f"{base_url}/api/v1/portal/orders/{order_id}/confirm-receipt"
    try:
        data = _api_call("POST", url, headers=_h(user_token), timeout=10)
        return data.get("code") == 0
    except Exception as exc:
        print(f"      确认收货失败: {exc}")
        return False


def complete_order(user_token: str, order_id: str, base_url: str) -> bool:
    """用户完成订单。"""
    url = f"{base_url}/api/v1/portal/orders/{order_id}/complete"
    try:
        data = _api_call("POST", url, headers=_h(user_token), timeout=10)
        return data.get("code") == 0
    except Exception as exc:
        print(f"      完成订单失败: {exc}")
        return False


def create_review(user_token: str, product_id: str, rating: int, content: str, base_url: str) -> dict | None:
    """创建评论。"""
    url = f"{base_url}/api/v1/portal/reviews"
    payload = {
        "product_id": product_id,
        "rating": rating,
        "content": content,
        "is_anonymous": random.choice([True, False]),
    }
    try:
        data = _api_call("POST", url, payload, _h(user_token), timeout=10)
        if data.get("code") == 0:
            return data["data"]
        else:
            # 可能是已评价过
            if "已评价" in data.get("message", "") or "reviewed" in data.get("message", "").lower():
                return None
            print(f"      创建评论失败: {data.get('message')}")
            return None
    except Exception as exc:
        print(f"      创建评论异常: {exc}")
        return None


def process_product(product: dict, users: list[dict], admin_token: str, base_url: str, reviews_per_product: int, orders_per_product: int) -> dict[str, Any]:
    """处理单个商品：创建订单和评论。"""
    product_id = product["id"]
    product_name = product["name"]
    sku_id = product["sku_id"]
    price = product.get("sku_price", product["price"])

    result = {"product_id": product_id, "product_name": product_name, "orders_created": 0, "reviews_created": 0, "errors": []}

    # 随机选择用户用于订单和评论
    random.shuffle(users)
    order_users = users[:orders_per_product]
    review_users = users[:reviews_per_product]

    # 1. 创建订单
    for i, user in enumerate(order_users):
        order = create_order_direct(user["token"], product_id, sku_id, random.randint(1, 3), price, base_url)
        if order:
            order_id = order["id"]
            time.sleep(0.2)
            # 支付
            if pay_order(user["token"], order_id, base_url):
                time.sleep(0.2)
                # admin 发货
                if deliver_order(admin_token, order_id, base_url):
                    time.sleep(0.2)
                    # 确认收货
                    if confirm_receipt(user["token"], order_id, base_url):
                        time.sleep(0.2)
                        # 完成订单
                        complete_order(user["token"], order_id, base_url)
                result["orders_created"] += 1
            else:
                result["errors"].append(f"order_pay_failed:{order_id}")
        time.sleep(0.2)

    # 2. 创建评论
    for i, user in enumerate(review_users):
        rating = random.choices([1, 2, 3, 4, 5], weights=[2, 3, 8, 15, 20])[0]
        content = random.choice(REVIEW_TEMPLATES)
        review = create_review(user["token"], product_id, rating, content, base_url)
        if review:
            result["reviews_created"] += 1
        time.sleep(0.1)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker: 导入用户活动数据")
    parser.add_argument("--task", type=int, required=True, help="任务编号")
    args = parser.parse_args()

    task_file = WORK_DIR / f"task_{args.task}.json"
    if not task_file.exists():
        print(f"任务文件不存在: {task_file}")
        sys.exit(1)

    with open(task_file, "r", encoding="utf-8") as f:
        task = json.load(f)

    products = task["products"]
    users = task["users"]
    admin_token = task["admin_token"]
    base_url = task["base_url"]
    reviews_per_product = task["reviews_per_product"]
    orders_per_product = task["orders_per_product"]
    worker_id = task["worker_id"]

    print(f"{'='*60}")
    print(f"Worker {worker_id} 启动")
    print(f"  商品数量: {len(products)}")
    print(f"  用户数量: {len(users)}")
    print(f"  每个商品订单: {orders_per_product}")
    print(f"  每个商品评论: {reviews_per_product}")
    print(f"{'='*60}\n")

    random.seed(42 + worker_id)

    total_orders = 0
    total_reviews = 0
    total_errors = 0

    for idx, product in enumerate(products, start=1):
        print(f"[{idx}/{len(products)}] 处理商品: {product['name'][:40]}...")
        try:
            result = process_product(product, users, admin_token, base_url, reviews_per_product, orders_per_product)
            total_orders += result["orders_created"]
            total_reviews += result["reviews_created"]
            total_errors += len(result["errors"])
            print(f"  ✓ 订单: {result['orders_created']}/{orders_per_product} | 评论: {result['reviews_created']}/{reviews_per_product}")
        except Exception as exc:
            print(f"  ✗ 处理失败: {exc}")
            total_errors += 1

    print(f"\n{'='*60}")
    print(f"Worker {worker_id} 完成")
    print(f"  订单创建: {total_orders}")
    print(f"  评论创建: {total_reviews}")
    print(f"  错误数: {total_errors}")
    print(f"{'='*60}")

    # 保存结果
    result_file = WORK_DIR / f"result_{worker_id}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "worker_id": worker_id,
            "total_orders": total_orders,
            "total_reviews": total_reviews,
            "total_errors": total_errors,
            "products_count": len(products),
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    main()
