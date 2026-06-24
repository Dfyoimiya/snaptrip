#!/usr/bin/env python3
"""Update SKU stock for the first 57 entries (index 0..56) from skus_for_stock_update.json."""

import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8080/api/v1"
SKU_FILE = "skus_for_stock_update.json"


def get_admin_token() -> str:
    login_url = f"{BASE_URL}/auth/login"
    body = json.dumps({"email": "admin@snaptrip.com", "password": "admin123"}).encode("utf-8")
    req = urllib.request.Request(
        login_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("data", {}).get("access_token")
    if not token:
        raise ValueError(f"No token in response: {data}")
    return token


def update_sku_stock(token: str, product_id: str, sku_id: str, stock: int) -> bool:
    put_url = f"{BASE_URL}/admin/products/{product_id}/skus?sku_id={sku_id}&stock={stock}"
    req = urllib.request.Request(
        put_url,
        headers={"Authorization": f"Bearer {token}"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _ = resp.read()
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  [FAIL] HTTP {e.code} for sku_id={sku_id}: {body}")
        return False
    except Exception as e:
        print(f"  [FAIL] Exception for sku_id={sku_id}: {e}")
        return False


def main() -> None:
    with open(SKU_FILE, "r", encoding="utf-8") as f:
        skus = json.load(f)

    target_skus = skus[:57]  # indexes 0..56
    print(f"Total SKUs in file: {len(skus)}")
    print(f"SKUs to process   : {len(target_skus)}\n")

    token = get_admin_token()
    print(f"Admin token acquired (len={len(token)}).\n")

    success_count = 0
    failed_skus = []

    for idx, sku in enumerate(target_skus, start=1):
        sku_id = sku["sku_id"]
        product_id = sku["product_id"]
        stock = sku["stock"]
        name = sku.get("product_name", "")[:50]

        print(f"[{idx}/{len(target_skus)}] Updating sku_id={sku_id} stock={stock} | {name}...")
        if update_sku_stock(token, product_id, sku_id, stock):
            success_count += 1
        else:
            failed_skus.append(sku_id)

        time.sleep(0.5)

    print("\n" + "=" * 50)
    print(f"Total processed : {len(target_skus)}")
    print(f"Success         : {success_count}")
    print(f"Failed          : {len(failed_skus)}")
    if failed_skus:
        print("Failed SKU IDs:")
        for sid in failed_skus:
            print(f"  - {sid}")
    print("=" * 50)


if __name__ == "__main__":
    main()
