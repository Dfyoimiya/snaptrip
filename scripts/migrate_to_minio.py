#!/usr/bin/env python3
"""迁移脚本 —— 将数据库中已有的 localhost 图片 URL 替换为 MinIO 代理 URL。

流程:
    1. 登录获取 admin token
    2. 扫描 mall-web/public/images/assets/ 下的所有本地图片
    3. 将每张图片上传到 MinIO (通过 admin upload API)
    4. 建立 旧URL → 新proxyURL 的映射
    5. 遍历所有商品, 替换 default_pic / pics / album_pics / description 中的旧 URL
    6. 调用 PUT /admin/products/{id} 更新商品

用法:
    python migrate_to_minio.py [--base-url http://localhost:8080] [--dry-run]

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# ── 配置 ──
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"

ASSET_DIR = Path("/Users/finley/01_Projects/Python_AI/snaptrip/mall-web/public/images/assets")
OLD_BASE_URLS = [
    "http://localhost:5173/images/assets/",
    "http://localhost:5175/images/assets/",
    "http://localhost:3000/images/assets/",
]

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _api_call(
    method: str, url: str, payload: dict | None = None,
    headers: dict | None = None, timeout: int = 30,
) -> dict:
    req_headers = headers.copy() if headers else {}
    if payload and "Content-Type" not in req_headers:
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
    data = _api_call("POST", f"{base_url}{API_PREFIX}/auth/login",
                     {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if data.get("code") != 0:
        raise RuntimeError(f"登录失败: {data.get('message')}")
    return data["data"]["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _encode_multipart(file_path: Path) -> tuple[bytes, str]:
    """构造 multipart/form-data 请求体 (仅单个文件字段)。"""
    boundary = uuid.uuid4().hex
    data = file_path.read_bytes()
    filename = file_path.name

    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.write(b"Content-Type: application/octet-stream\r\n")
    body.write(b"\r\n")
    body.write(data)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("utf-8"))

    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def upload_image(token: str, file_path: Path, base_url: str = BASE_URL) -> dict:
    url = f"{base_url}{API_PREFIX}/admin/upload/image"
    body, ct = _encode_multipart(file_path)
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
        raise RuntimeError(f"上传失败 [{file_path.name}]: HTTP {exc.code}: {error_body}")
    if data.get("code") != 0:
        raise RuntimeError(f"上传失败 [{file_path.name}]: {data.get('message')}")
    return data["data"]


def build_url_mapping(token: str, base_url: str = BASE_URL) -> dict[str, str]:
    """扫描本地图片 → 上传到 MinIO → 返回 {old_url: new_proxy_url} 映射。"""
    mapping: dict[str, str] = {}
    if not ASSET_DIR.exists():
        print(f"素材目录不存在: {ASSET_DIR}")
        return mapping

    files = sorted([
        f for f in ASSET_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
    ])
    total = len(files)
    print(f"发现 {total} 张本地图片")

    for idx, file_path in enumerate(files, 1):
        try:
            result = upload_image(token, file_path, base_url)
            object_name = result["object_name"]
            proxy_url = f"/api/v1/images/{object_name}"

            # 从文件路径构建旧 URL
            rel = file_path.relative_to(ASSET_DIR)
            for old_base in OLD_BASE_URLS:
                old_url = old_base + str(rel)
                mapping[old_url] = proxy_url

            if idx % 20 == 0 or idx == total:
                print(f"  [{idx}/{total}] 已上传")
        except Exception as exc:
            print(f"  [{idx}/{total}] 跳过 {file_path.name}: {exc}")

    print(f"建成 {len(mapping)} 条 URL 映射")
    return mapping


def replace_urls(text: str | None, mapping: dict[str, str]) -> str | None:
    """替换文本中所有匹配的旧 URL。"""
    if not text:
        return text
    result = text
    for old_url, new_url in mapping.items():
        result = result.replace(old_url, new_url)
    return result


def migrate_products(token: str, mapping: dict[str, str], dry_run: bool, base_url: str = BASE_URL) -> int:
    """遍历所有商品, 替换图片 URL 并更新。"""
    if not mapping:
        print("URL 映射为空，跳过商品迁移")
        return 0

    # 获取所有商品
    page = 1
    page_size = 50
    updated = 0

    while True:
        list_url = f"{base_url}{API_PREFIX}/admin/products?page={page}&page_size={page_size}"
        data = _api_call("GET", list_url, headers=_headers(token))
        if data.get("code") != 0:
            print(f"获取商品列表失败: {data.get('message')}")
            break

        page_data = data.get("data", {})
        items = page_data.get("items", [])
        if not items:
            break

        for product in items:
            product_id = product["id"]
            old_pics = product.get("pics") or ""
            old_album = product.get("albumPics") or ""
            old_default = product.get("defaultPic") or ""
            old_desc = product.get("description") or ""

            new_pics = replace_urls(old_pics, mapping)
            new_album = replace_urls(old_album, mapping)
            new_default = replace_urls(old_default, mapping)
            new_desc = replace_urls(old_desc, mapping)

            # 检查是否需要更新
            if (new_pics == old_pics and new_album == old_album
                    and new_default == old_default and new_desc == old_desc):
                continue

            if dry_run:
                print(f"  [DRY RUN] {product['name']}:")
                if new_default != old_default:
                    print(f"    default_pic: {old_default[:60]}... → {new_default[:60]}...")
                if new_pics != old_pics:
                    print(f"    pics: {old_pics[:60]}... → {new_pics[:60]}...")
                updated += 1
                continue

            payload = {
                "pics": new_pics,
                "album_pics": new_album,
                "default_pic": new_default,
                "description": new_desc,
            }
            try:
                update_url = f"{base_url}{API_PREFIX}/admin/products/{product_id}"
                _api_call("PUT", update_url, payload, _headers(token))
                print(f"  ✓ {product['name']}")
                updated += 1
                time.sleep(0.1)
            except Exception as exc:
                print(f"  ✗ {product['name']}: {exc}")

        if len(items) < page_size:
            break
        page += 1

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="本地图片 → MinIO 迁移脚本")
    parser.add_argument("--base-url", type=str, default=BASE_URL, help="后端基础URL")
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不执行更新")
    parser.add_argument("--skip-upload", action="store_true", help="跳过上传 (使用已有映射)")
    args = parser.parse_args()

    print(f"登录到 {args.base_url} ...")
    token = login(args.base_url)
    print("登录成功\n")

    if args.skip_upload:
        print("跳过图片上传")
        mapping = {}
    else:
        print("上传本地图片到 MinIO...")
        mapping = build_url_mapping(token, args.base_url)

    print(f"\n迁移商品图片 URL ({'DRY RUN' if args.dry_run else '实际更新'})...")
    count = migrate_products(token, mapping, dry_run=args.dry_run, base_url=args.base_url)

    action = "需要更新" if args.dry_run else "已更新"
    print(f"\n总计: {count} 个商品 {action}")


if __name__ == "__main__":
    main()
