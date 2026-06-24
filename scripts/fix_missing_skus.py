#!/usr/bin/env python3
"""为缺少SKU的商品补创建默认SKU。"""

import json
import re
import urllib.request
import urllib.error

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


def create_sku(token: str, product_id: str, product_name: str) -> bool:
    sku_code = re.sub(r'[^\w]', '', product_name)[:20] or f"SKU{product_id[:8]}"
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
        print(f"  SKU 失败: {result}")
        return False
    print(f"  ✅ SKU 创建成功")
    return True


def main():
    import psycopg2
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    cur = conn.cursor()
    cur.execute('''
        SELECT p.id, p.name
        FROM pms_products p
        LEFT JOIN pms_skus s ON p.id = s.product_id
        WHERE s.id IS NULL AND p.created_at > '2026-06-23 21:00:00'
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"找到 {len(rows)} 个缺少SKU的商品")
    if not rows:
        return

    token = login()
    print(f"登录成功\n")

    success = 0
    failed = 0
    for idx, (product_id, product_name) in enumerate(rows, 1):
        print(f"[{idx}/{len(rows)}] {product_name[:60]}")
        if create_sku(token, product_id, product_name):
            success += 1
        else:
            failed += 1

    print(f"\n完成: 成功 {success}, 失败 {failed}, 总计 {len(rows)}")


if __name__ == "__main__":
    main()
