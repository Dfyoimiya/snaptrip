#!/usr/bin/env python3
"""Update SKU stock for index 57-114."""

import json
import time
import requests


def main():
    # 1. Read SKU file
    with open("skus_for_stock_update.json", "r", encoding="utf-8") as f:
        skus = json.load(f)

    # 2. Slice index 57 to 114 (inclusive) -> 58 items
    target_skus = skus[57:115]
    print(f"Total SKUs selected: {len(target_skus)}")

    # 3. Login to get admin token
    login_url = "http://localhost:8080/api/v1/auth/login"
    login_body = {"email": "admin@snaptrip.com", "password": "admin123"}
    resp = requests.post(login_url, json=login_body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    token = data["data"]["access_token"]
    print("Login successful, token acquired.")

    headers = {"Authorization": f"Bearer {token}"}
    success_count = 0
    failed_skus = []

    # 4. Update each SKU
    for idx, sku in enumerate(target_skus, start=1):
        sku_id = sku["sku_id"]
        product_id = sku["product_id"]
        stock = sku["stock"]
        url = f"http://localhost:8080/api/v1/admin/products/{product_id}/skus?sku_id={sku_id}&stock={stock}"

        try:
            put_resp = requests.put(url, headers=headers, timeout=30)
            put_resp.raise_for_status()
            success_count += 1
            print(f"[{idx}/{len(target_skus)}] OK  sku_id={sku_id} stock={stock}")
        except Exception as e:
            failed_skus.append(sku_id)
            print(f"[{idx}/{len(target_skus)}] FAIL sku_id={sku_id} stock={stock} error={e}")

        # 5. Sleep to avoid rate limiting
        time.sleep(0.5)

    # 6. Print summary
    print("\n========== Summary ==========")
    print(f"Success: {success_count}")
    print(f"Failed:  {len(failed_skus)}")
    if failed_skus:
        print("Failed SKU IDs:")
        for sid in failed_skus:
            print(f"  - {sid}")
    print("==============================")


if __name__ == "__main__":
    main()
