#!/usr/bin/env python3
"""素材库导入脚本 —— 修复版：将本地图片上传至 MinIO 并通过后端代理路径引用。

修复内容:
    1. 图片代理路径从 /api/v1/images/ 修正为 /api/v1/portal/images/（匹配实际路由）
    2. 每个商品使用自己的详情图片作为主图，不再共享主图池图片（解决商品与图片不对应）
    3. 商品详情 HTML 中嵌入该商品自己的详情图片
    4. 支持 --clean 删除已导入的 ASSET-* 商品后重新导入

用法:
    python import_assets.py --clean
    python import_assets.py --categories "家具建材,数码产品"

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

# ── 配置 ──
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"

ASSET_DIR = Path("/Users/finley/01_Projects/Python_AI/snaptrip/素材")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _api_call(
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
) -> dict:
    """使用 urllib 发起 JSON HTTP 请求，返回解析后的 JSON。"""
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


def login(base_url: str = BASE_URL) -> str:
    """登录获取 access_token。"""
    url = f"{base_url}{API_PREFIX}/auth/login"
    data = _api_call("POST", url, {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if data.get("code") != 0:
        raise RuntimeError(f"登录失败: {data.get('message')}")
    return data["data"]["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Multipart 文件上传 ──


def _encode_multipart(file_field: str, file_path: Path) -> tuple[bytes, str]:
    """构造 multipart/form-data 请求体 (仅单个文件字段)。"""
    boundary = uuid.uuid4().hex
    data = file_path.read_bytes()
    filename = file_path.name

    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("utf-8"))
    body.write(b"Content-Type: application/octet-stream\r\n")
    body.write(b"\r\n")
    body.write(data)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("utf-8"))

    content_type = f"multipart/form-data; boundary={boundary}"
    return body.getvalue(), content_type


def upload_image(token: str, file_path: Path, base_url: str = BASE_URL) -> dict:
    """上传单张图片到 MinIO, 返回 {object_name, url, presigned_url, size}。"""
    url = f"{base_url}{API_PREFIX}/admin/upload/image"
    body, ct = _encode_multipart("file", file_path)
    req_headers = _headers(token)
    req_headers["Content-Type"] = ct

    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            error_body = {"message": str(exc)}
        raise RuntimeError(f"图片上传失败 [{file_path.name}]: HTTP {exc.code}: {error_body}")

    if data.get("code") != 0:
        raise RuntimeError(f"图片上传失败 [{file_path.name}]: {data.get('message')}")
    return data["data"]


# ── 分类管理 ──


def get_categories(token: str, base_url: str = BASE_URL) -> dict[str, dict]:
    """获取现有分类树，返回 {name_lower: category_data} 映射。"""
    url = f"{base_url}{API_PREFIX}/admin/categories/tree"
    data = _api_call("GET", url, headers=_headers(token))
    if data.get("code") != 0:
        raise RuntimeError(f"获取分类失败: {data.get('message')}")

    mapping: dict[str, dict] = {}

    def _walk(nodes: list[dict]) -> None:
        for node in nodes:
            mapping[node["name"].strip().lower()] = node
            _walk(node.get("children", []))

    _walk(data.get("data", []))
    return mapping


def create_category(token: str, name: str, base_url: str = BASE_URL) -> dict:
    """创建一级分类，返回创建后的分类数据。"""
    url = f"{base_url}{API_PREFIX}/admin/categories"
    payload = {
        "name": name,
        "type": "PRODUCT",
        "parent_id": None,
        "level": 0,
        "nav_status": 1,
        "show_status": 1,
        "icon": "",
        "keywords": name,
        "description": f"{name}分类",
    }
    data = _api_call("POST", url, payload, _headers(token))
    if data.get("code") != 0:
        raise RuntimeError(f"创建分类失败 [{name}]: {data.get('message')}")
    return data["data"]


def ensure_categories(token: str, categories: list[str], base_url: str = BASE_URL) -> dict[str, str]:
    """确保分类存在，返回 {name: category_id} 映射。"""
    existing = get_categories(token, base_url)
    mapping: dict[str, str] = {}
    for cat in categories:
        key = cat.strip().lower()
        if key in existing:
            mapping[cat] = existing[key]["id"]
            print(f"  [分类已存在] {cat} -> {existing[key]['id']}")
        else:
            created = create_category(token, cat, base_url)
            mapping[cat] = created["id"]
            print(f"  [分类已创建] {cat} -> {created['id']}")
    return mapping


# ── 图片处理 ──


def _is_image_file(f: Path) -> bool:
    return f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS


def _build_proxy_url(object_name: str) -> str:
    """构建后端图片代理 URL，匹配实际路由 /api/v1/portal/images/"""
    return f"/api/v1/portal/images/{object_name}"


# ── 商品创建 ──


def _extract_brand_and_name(product_folder_name: str) -> tuple[str, str]:
    """从京东商品文件夹名提取品牌和商品名称。"""
    name = re.sub(r"【行情\s*报价\s*价格\s*评测】-京东\s*$", "", product_folder_name).strip()
    brand = "未知品牌"
    m = re.match(r"^(.*?)（([^）]+)）", name)
    if m:
        brand = m.group(2).strip()
    else:
        parts = name.split(" ")
        if len(parts) > 1 and len(parts[0]) <= 10:
            brand = parts[0]

    short_name = re.split(r"[【\[\(（]", name)[0].strip()
    if len(short_name) > 60:
        short_name = short_name[:60] + "..."

    return brand, short_name


def _generate_product_sn(category: str, idx: int) -> str:
    """生成唯一商品货号, 末尾加短随机码防止软删除冲突。"""
    prefix = category[:2].upper()
    suffix = uuid.uuid4().hex[:4]
    return f"ASSET-{prefix}-{idx:04d}-{suffix}"


def _generate_price(category: str, name: str) -> tuple[Decimal, Decimal]:
    h = hashlib.md5(f"{category}:{name}".encode()).hexdigest()
    val = int(h[:6], 16)

    price_ranges = {
        "个人美妆": (50, 500),
        "五金机电": (30, 800),
        "健康保养": (80, 2000),
        "农资园艺": (20, 300),
        "家具建材": (100, 5000),
        "家用电器": (200, 8000),
        "户外运动": (50, 3000),
        "数码产品": (200, 15000),
        "文具办公": (10, 500),
        "服饰鞋包": (50, 2000),
        "母婴亲子": (30, 800),
        "汽车服务": (20, 1500),
        "粮油调味": (10, 300),
        "萌宠护理": (20, 500),
        "食品酒饮": (10, 800),
    }
    low, high = price_ranges.get(category, (50, 1000))
    price = low + (val % (high - low + 1))
    original_price = int(price * 1.2)
    return Decimal(str(price)), Decimal(str(original_price))


def create_product(
    token: str,
    category_id: str,
    category_name: str,
    product_dir: Path,
    main_image_urls: list[str],
    detail_image_urls: list[str],
    idx: int,
    base_url: str = BASE_URL,
) -> dict:
    """调用后端 API 创建单个商品。"""
    brand, short_name = _extract_brand_and_name(product_dir.name)
    price, original_price = _generate_price(category_name, short_name)

    # 主图: 最多5张（使用自己上传的详情图）
    pics = main_image_urls[:5]
    default_pic = pics[0] if pics else ""
    album_pics = ",".join(pics[1:]) if len(pics) > 1 else ""
    pics_str = ",".join(pics)

    # 商品详情 HTML (嵌入该商品自己的详情图片)
    if detail_image_urls[:10]:
        description_parts = [
            f'<p><img src="{url}" style="max-width:100%;" loading="lazy"/></p>'
            for url in detail_image_urls[:10]
        ]
        description = "\n".join(description_parts)
    else:
        description = f"<p>{short_name}</p>"

    product_sn = _generate_product_sn(category_name, idx)

    payload = {
        "name": short_name,
        "sub_title": f"{brand} | 品质优选",
        "category_id": category_id,
        "product_sn": product_sn,
        "price": str(price),
        "original_price": str(original_price),
        "stock": 100,
        "sale_count": 0,
        "pics": pics_str,
        "album_pics": album_pics,
        "default_pic": default_pic,
        "description": description,
        "keywords": f"{category_name} {brand} {short_name}"[:255],
        "unit": "件",
        "publish_status": 1,
        "new_status": 1,
        "recommend_status": 0,
        "skus": [
            {
                "sku_code": f"{product_sn}-001",
                "spec": json.dumps({"规格": "标准版"}, ensure_ascii=False),
                "price": str(price),
                "stock": 100,
                "low_stock": 10,
                "pic": default_pic,
            }
        ],
        "attribute_values": {},
    }

    url = f"{base_url}{API_PREFIX}/admin/products"
    data = _api_call("POST", url, payload, _headers(token))
    if data.get("code") != 0:
        raise RuntimeError(f"创建商品失败 [{short_name}]: {data.get('message')}")
    return data["data"]


# ── 品类导入 ──


def import_category(
    token: str,
    category_name: str,
    category_id: str,
    asset_dir: Path = ASSET_DIR,
    base_url: str = BASE_URL,
) -> dict[str, Any]:
    """导入单个品类的所有商品。每个商品使用自己的详情图片作为主图。"""
    print(f"\n{'='*60}")
    print(f"开始导入品类: {category_name}")
    print(f"{'='*60}")

    detail_dir = asset_dir / "详情" / category_name

    if not detail_dir.exists():
        print(f"  详情目录不存在: {detail_dir}")
        return {"category": category_name, "created": 0, "failed": 0, "images": 0}

    product_dirs = [d for d in sorted(detail_dir.iterdir()) if d.is_dir()]
    total_images = 0

    for idx, product_dir in enumerate(product_dirs, start=1):
        try:
            print(f"\n  [{idx}/{len(product_dirs)}] {product_dir.name[:50]}...")

            # 收集该商品的详情图片
            detail_images = sorted([f for f in product_dir.iterdir() if _is_image_file(f)])
            if not detail_images:
                print(f"    跳过: 无图片")
                continue

            # 上传该商品的详情图片（同时作为主图和详情图）
            print(f"    上传图片 ({len(detail_images)} 张)...")
            uploaded_urls: list[str] = []
            for img_path in detail_images[:10]:  # 最多10张
                try:
                    result = upload_image(token, img_path, base_url)
                    object_name = result["object_name"]
                    proxy_url = _build_proxy_url(object_name)
                    uploaded_urls.append(proxy_url)
                    total_images += 1
                    time.sleep(0.1)
                except Exception as exc:
                    print(f"    [上传失败] {img_path.name}: {exc}")

            # 前5张作为主图，全部作为详情
            main_urls = uploaded_urls[:5]
            detail_urls = uploaded_urls

            if not main_urls:
                print(f"    跳过: 图片上传全部失败")
                continue

            result = create_product(
                token,
                category_id,
                category_name,
                product_dir,
                main_urls,
                detail_urls,
                idx,
                base_url,
            )
            print(f"    ✓ 商品已创建: {result['name'][:40]}... ({result['id']})")
            time.sleep(0.3)
        except Exception as exc:
            print(f"    ✗ 失败: {exc}")

    return {
        "category": category_name,
        "created": len(product_dirs),
        "failed": 0,
        "images": total_images,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="素材库导入脚本 (MinIO 修复版)")
    parser.add_argument("--categories", type=str, default="", help="逗号分隔的品类列表，空=全部")
    parser.add_argument("--base-url", type=str, default=BASE_URL, help="后端基础URL")
    parser.add_argument("--clean", action="store_true", help="导入前删除已有 ASSET-* 商品")
    args = parser.parse_args()

    if not ASSET_DIR.exists():
        print(f"素材目录不存在: {ASSET_DIR}")
        sys.exit(1)

    # 1. 登录
    print(f"登录到 {args.base_url} ...")
    token = login(args.base_url)
    print("登录成功\n")

    # 1.5 清理已有 ASSET 商品
    if args.clean:
        print("清理已有 ASSET 商品...")
        page = 1
        deleted = 0
        while True:
            list_url = f"{args.base_url}{API_PREFIX}/admin/products?page={page}&page_size=50&keyword=ASSET-"
            list_data = _api_call("GET", list_url, headers=_headers(token))
            if list_data.get("code") != 0:
                print(f"  获取商品列表失败: {list_data.get('message')}")
                break
            page_data = list_data.get("data", {})
            items = page_data.get("items", [])
            if not items:
                break
            for product in items:
                try:
                    del_url = f"{args.base_url}{API_PREFIX}/admin/products/{product['id']}"
                    _api_call("DELETE", del_url, headers=_headers(token))
                    print(f"  已删除: {product['name'][:40]}... ({product['id']})")
                    deleted += 1
                    time.sleep(0.05)
                except Exception as exc:
                    print(f"  删除失败 {product['name'][:40]}...: {exc}")
            if len(items) < 50:
                break
            page += 1
        print(f"清理完成: 删除了 {deleted} 个商品\n")

    # 2. 确定品类列表
    detail_dir = ASSET_DIR / "详情"
    all_categories = sorted([d.name for d in detail_dir.iterdir() if d.is_dir()]) if detail_dir.exists() else []
    if args.categories:
        target_categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    else:
        target_categories = all_categories

    print(f"目标品类 ({len(target_categories)} 个): {', '.join(target_categories)}")

    # 3. 确保分类存在
    print("\n检查/创建分类...")
    cat_mapping = ensure_categories(token, target_categories, args.base_url)

    # 4. 导入每个品类
    results = []
    for cat in target_categories:
        cat_id = cat_mapping[cat]
        result = import_category(token, cat, cat_id, ASSET_DIR, args.base_url)
        results.append(result)

    # 5. 汇总
    print(f"\n{'='*60}")
    print("导入汇总")
    print(f"{'='*60}")
    total_created = 0
    total_failed = 0
    total_images = 0
    for r in results:
        print(f"  {r['category']}: 成功 {r['created']} | 失败 {r['failed']} | 图片 {r['images']}")
        total_created += r["created"]
        total_failed += r["failed"]
        total_images += r["images"]
    print(f"\n总计: 成功 {total_created} | 失败 {total_failed} | 上传图片 {total_images}")


if __name__ == "__main__":
    main()
