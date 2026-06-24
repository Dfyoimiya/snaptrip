#!/usr/bin/env python3
"""清理数据库中商品的混图：移除京东宣传图，保留正确图片，删除图片不足的商品。"""

import json
import re
import urllib.request
import urllib.error
import psycopg2

BASE_URL = "http://localhost:8080"
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"


def _make_request(method, path, headers=None, data=None, timeout=30):
    url = f"{BASE_URL}{path}"
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
    payload = json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode()
    headers = {"Content-Type": "application/json"}
    result = _make_request("POST", "/api/v1/auth/login", headers=headers, data=payload)
    if result.get("code") != 0:
        print(f"登录失败: {result}")
        exit(1)
    return result["data"]["access_token"]


def update_product(token, product_id, default_pic, pics, album_pics, description):
    """更新商品图片和描述。"""
    payload = {
        "default_pic": default_pic,
        "pics": pics,
        "album_pics": album_pics,
        "description": description,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "PUT", f"/api/v1/admin/products/{product_id}",
        headers=headers, data=json.dumps(payload).encode()
    )
    return result.get("code") == 0


def delete_product(token, product_id):
    """删除商品。"""
    headers = {"Authorization": f"Bearer {token}"}
    result = _make_request(
        "DELETE", f"/api/v1/admin/products/{product_id}",
        headers=headers
    )
    return result.get("code") == 0


def main():
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    cur = conn.cursor()

    # 获取所有导入商品
    cur.execute("""
        SELECT id, name, default_pic, pics, album_pics, description
        FROM pms_products
        WHERE created_at > '2026-06-23 20:00:00'
    """)
    products = cur.fetchall()
    cur.close()
    conn.close()

    print(f"找到 {len(products)} 个导入商品")
    token = login()
    print(f"登录成功\n")

    kept = 0      # 保留并更新
    deleted = 0   # 删除（图片不足）
    skipped = 0   # 无需处理

    for idx, (pid, name, default_pic, pics, album_pics, desc) in enumerate(products, 1):
        # 解析所有图片 URL
        all_urls = []
        if pics:
            all_urls.extend([u.strip() for u in pics.split(',') if u.strip()])
        if album_pics:
            all_urls.extend([u.strip() for u in album_pics.split(',') if u.strip()])
        
        # 去重并保持顺序
        seen = set()
        unique_urls = []
        for u in all_urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)

        # 检查是否有 URL 重复（可能是混图的信号）
        if len(all_urls) != len(unique_urls):
            print(f"[{idx}/{len(products)}] ⚠️ {name[:50]}... 有重复URL")

        # 策略：只保留前5张作为 pics，清空 album_pics
        if len(unique_urls) >= 3:
            new_default_pic = unique_urls[0]
            new_pics = ','.join(unique_urls[:5])
            new_album_pics = ''
            # 更新 description：只包含前5张图片
            desc_parts = [f'<p>{name}</p>']
            for url in unique_urls[:5]:
                desc_parts.append(f'<p><img src="{url}" style="max-width:100%; display:block; margin-bottom:12px;" /></p>')
            new_description = '\n'.join(desc_parts)

            if update_product(token, pid, new_default_pic, new_pics, new_album_pics, new_description):
                print(f"[{idx}/{len(products)}] ✅ 保留: {name[:50]}... ({len(unique_urls)}→{min(len(unique_urls),5)}张)")
                kept += 1
            else:
                print(f"[{idx}/{len(products)}] ❌ 更新失败: {name[:50]}...")
        elif len(unique_urls) >= 1:
            # 图片1-2张，删除商品
            if delete_product(token, pid):
                print(f"[{idx}/{len(products)}] 🗑️ 删除（图片不足）: {name[:50]}... ({len(unique_urls)}张)")
                deleted += 1
            else:
                print(f"[{idx}/{len(products)}] ❌ 删除失败: {name[:50]}...")
        else:
            # 无图片，删除
            if delete_product(token, pid):
                print(f"[{idx}/{len(products)}] 🗑️ 删除（无图片）: {name[:50]}...")
                deleted += 1
            else:
                print(f"[{idx}/{len(products)}] ❌ 删除失败: {name[:50]}...")

    print(f"\n完成: 保留 {kept}, 删除 {deleted}, 总计 {len(products)}")


if __name__ == "__main__":
    main()
