#!/usr/bin/env python3
"""
素材商品重新导入脚本 - 正确版本
使用后端图片上传API → MinIO → 代理URL
确保每个商品使用自己的详情图片

Usage:
    python import_products_correct.py [category_name]
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

BASE_URL = "http://localhost:8080"
ASSETS_DIR = Path("素材/详情")
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"

# 素材分类 → 后端分类ID 映射
CATEGORY_MAP = {
    "数码产品": "ef31fcac-1800-4c9a-a8f3-4f8b56338ed6",
    "服饰鞋包": "494d6b90-6e61-47a1-9708-156b598a0b9a",
    "食品酒饮": "ea9b2a2c-8105-49ff-ad3c-342f9be2ce2c",
    "个人美妆": "7bb4afaa-fabb-450e-a846-67cc9bb7b810",
    "五金机电": "a6e5ac39-afcf-4b4f-9a62-e9f3a2c27fa9",
    "健康保养": "f4787b79-119f-47cf-a796-5eb5c0b4e74b",
    "文具办公": "fe8e34c9-ad79-4075-b29b-209befb37bb3",
    "母婴亲子": "16a8bbfd-28ff-498a-9b32-1cad8289e15d",
    "农资园艺": "badb6696-b505-4e39-8179-d63488afc4a1",
    "汽车服务": "9f744378-067d-4343-9e98-91620c970c2e",
    "粮油调味": "7ba8c057-d961-4dd7-b5e9-29953e17b707",
    "萌宠护理": "257409bc-c289-4332-ace6-d2a013e70f9b",
    "户外运动": "00fb465c-28ac-4445-8db7-5e22128c576f",
    "家具建材": "f06373c9-90d2-4890-a512-b8b6d632308d",
    "家用电器": "681c947c-66dd-5c98-bc8d-f2681005a960",
}


def _make_request(
    method: str,
    path: str,
    headers: Optional[dict] = None,
    data: Optional[bytes] = None,
    timeout: int = 30,
) -> dict:
    """发起 HTTP 请求并返回 JSON 结果。"""
    url = f"{BASE_URL}{path}" if not path.startswith("http") else path
    req = urllib.request.Request(url, method=method, data=data)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {"code": 0, "data": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return json.loads(body)
        except Exception:
            return {"code": e.code, "message": str(e.reason), "data": None}
    except Exception as e:
        return {"code": -1, "message": str(e), "data": None}


def login() -> str:
    """登录获取 admin token。"""
    payload = json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode()
    headers = {"Content-Type": "application/json"}
    result = _make_request("POST", "/api/v1/auth/login", headers=headers, data=payload)
    if result.get("code") != 0:
        print(f"登录失败: {result}")
        sys.exit(1)
    return result["data"]["access_token"]


def upload_image(token: str, file_path: Path) -> dict:
    """上传图片到 MinIO，返回 {object_name, url, proxy_url}。"""
    # multipart/form-data 手动构造
    boundary = f"----WebKitFormBoundary{os.urandom(16).hex()}"
    with open(file_path, "rb") as f:
        file_data = f.read()

    filename = file_path.name
    content_type = "image/jpeg"
    if filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".webp"):
        content_type = "image/webp"

    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: {content_type}\r\n\r\n'
    ).encode() + file_data + f'\r\n--{boundary}--\r\n'.encode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    result = _make_request("POST", "/api/v1/admin/upload/image", headers=headers, data=body)
    if result.get("code") != 0:
        print(f"  上传失败: {result}")
        return None

    data = result["data"]
    object_name = data["object_name"]
    # 正确的代理 URL（不是 /portal/images/，而是 /images/）
    proxy_url = f"/api/v1/images/{object_name}"
    return {
        "object_name": object_name,
        "url": data["url"],
        "proxy_url": proxy_url,
        "size": data.get("size", 0),
    }


def create_product(token: str, category_id: str, category_name: str,
                   product_name: str, image_urls: list[str]) -> Optional[str]:
    """创建商品，返回商品 ID。"""
    if not image_urls:
        print(f"  警告：没有图片，跳过")
        return None

    # default_pic = 第一张
    default_pic = image_urls[0]
    # pics = 前5张
    pics = ",".join(image_urls[:5])
    # album_pics = 剩余
    album_pics = ",".join(image_urls[5:]) if len(image_urls) > 5 else ""

    # description = HTML 嵌入所有图片
    desc_parts = []
    for url in image_urls:
        desc_parts.append(f'<p><img src="{url}" style="max-width:100%; margin-bottom:12px;" /></p>')
    description = "\n".join(desc_parts)

    # 从名称中提取品牌（第一个空格前的词）
    brand_match = re.match(r'^([^\s]+)', product_name)
    brand = brand_match.group(1) if brand_match else ""

    payload = {
        "name": product_name,
        "category_id": category_id,
        "brand": brand,
        "description": description,
        "default_pic": default_pic,
        "pics": pics,
        "album_pics": album_pics,
        "price": 99.0,
        "original_price": 199.0,
        "stock": 100,
        "low_stock": 10,
        "unit": "件",
        "weight": 1.0,
        "preview_status": 1,
        "publish_status": 1,
        "recommand_status": 1,
        "service_ids": "1,2",
        "detail_title": product_name,
        "detail_desc": description,
        "keywords": category_name,
        "note": "",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "POST", "/api/v1/admin/products",
        headers=headers, data=json.dumps(payload).encode()
    )
    if result.get("code") != 0:
        print(f"  创建商品失败: {result}")
        return None

    product_id = result["data"]["id"] if isinstance(result["data"], dict) else result["data"]
    print(f"  ✅ 创建商品成功: {product_id}")
    return product_id


def create_sku(token: str, product_id: str, product_name: str) -> bool:
    """为商品创建默认 SKU。"""
    sku_code = re.sub(r'[^\w]', '', product_name)[:20] + f"_{int(time.time())%100000}" if product_name else f"SKU{int(time.time())}"
    payload = {
        "product_id": product_id,
        "sku_code": sku_code,
        "spec": "{}",
        "price": 99.0,
        "stock": 100,
        "low_stock": 10,
        "pic": "",
        "sale": 0,
        "promotion_price": 89.0,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "POST", f"/api/v1/admin/products/{product_id}/skus",
        headers=headers, data=json.dumps(payload).encode()
    )
    if result.get("code") != 0:
        print(f"  创建 SKU 失败: {result}")
        return False
    print(f"  ✅ 创建 SKU 成功")
    return True


def process_category(token: str, category_name: str) -> dict:
    """处理单个分类下的所有商品。"""
    category_id = CATEGORY_MAP.get(category_name)
    if not category_id:
        print(f"未找到分类映射: {category_name}")
        return {"total": 0, "success": 0, "failed": 0}

    category_dir = ASSETS_DIR / category_name
    if not category_dir.exists():
        print(f"目录不存在: {category_dir}")
        return {"total": 0, "success": 0, "failed": 0}

    product_dirs = [d for d in category_dir.iterdir() if d.is_dir()]
    total = len(product_dirs)
    success = 0
    failed = 0

    print(f"\n{'='*60}")
    print(f"处理分类: {category_name} ({total} 个商品)")
    print(f"{'='*60}")

    for idx, product_dir in enumerate(product_dirs, 1):
        product_name = product_dir.name
        # 清理名称中的京东后缀
        product_name = re.sub(r'【行情 报价 价格 评测】-京东$', '', product_name).strip()
        product_name = re.sub(r'【行情 报价 价格 评测】$', '', product_name).strip()

        print(f"\n[{idx}/{total}] {product_name}")

        # 收集该商品的所有图片
        image_files = sorted(
            [f for f in product_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]
        )
        if not image_files:
            print(f"  跳过：没有图片")
            failed += 1
            continue

        # 上传所有图片
        image_urls = []
        for img_path in image_files:
            print(f"  上传: {img_path.name}")
            upload_result = upload_image(token, img_path)
            if upload_result:
                image_urls.append(upload_result["proxy_url"])
                time.sleep(0.2)  # 避免速率限制
            else:
                print(f"  上传失败，跳过该图片")

        if not image_urls:
            print(f"  跳过：所有图片上传失败")
            failed += 1
            continue

        # 创建商品
        product_id = create_product(token, category_id, category_name, product_name, image_urls)
        if product_id:
            create_sku(token, product_id, product_name)
            success += 1
        else:
            failed += 1

        time.sleep(0.5)

    print(f"\n分类 {category_name} 完成: 成功 {success}, 失败 {failed}, 总计 {total}")
    return {"total": total, "success": success, "failed": failed}


def main():
    token = login()
    print(f"登录成功，获取 token: {token[:20]}...")

    # 如果指定了分类名，只处理该分类
    if len(sys.argv) > 1:
        category_name = sys.argv[1]
        if category_name not in CATEGORY_MAP:
            print(f"未知的分类: {category_name}")
            print(f"可用分类: {', '.join(CATEGORY_MAP.keys())}")
            sys.exit(1)
        process_category(token, category_name)
    else:
        # 处理所有分类
        results = {}
        for category_name in CATEGORY_MAP.keys():
            results[category_name] = process_category(token, category_name)

        print(f"\n{'='*60}")
        print("导入完成汇总")
        print(f"{'='*60}")
        total_all = sum(r["total"] for r in results.values())
        success_all = sum(r["success"] for r in results.values())
        failed_all = sum(r["failed"] for r in results.values())
        print(f"总计: {total_all}, 成功: {success_all}, 失败: {failed_all}")
        for cat, res in results.items():
            print(f"  {cat}: {res['success']}/{res['total']}")


if __name__ == "__main__":
    main()
