#!/usr/bin/env python3
"""清理旧错误商品数据 — 删除 default_pic 包含 localhost 的商品及关联数据。"""

import psycopg2

import os

env_path = os.path.join(os.path.dirname(__file__), ".env")
password = "snaptrip_dev_pass"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    password = parts[2].split("@")[0]
                break

conn = psycopg2.connect(
    host="localhost", port=5432, database="snaptrip_dev",
    user="snaptrip", password=password
)
conn.autocommit = False
cur = conn.cursor()

try:
    # 1. 找出所有包含 localhost 的商品ID
    cur.execute("SELECT id FROM pms_products WHERE default_pic LIKE '%localhost%'")
    bad_ids = [row[0] for row in cur.fetchall()]
    print(f"找到 {len(bad_ids)} 个错误商品（含 localhost）")

    # 2. 同时找出今天 21:29 之后测试导入的商品（已经使用正确URL的重复商品）
    cur.execute("""
        SELECT id FROM pms_products
        WHERE created_at > '2026-06-23 21:28:00'
          AND created_at > (SELECT MAX(created_at) FROM pms_products WHERE default_pic LIKE '%localhost%')
    """)
    test_ids = [row[0] for row in cur.fetchall()]
    print(f"找到 {len(test_ids)} 个测试导入商品（今日21:29后）")

    all_ids = list(set(bad_ids + test_ids))
    if not all_ids:
        print("没有需要删除的商品")
        conn.commit()
        exit(0)

    print(f"总计需要删除 {len(all_ids)} 个商品")

    # 3. 删除关联数据（按外键依赖顺序）
    # 评论
    cur.execute("DELETE FROM pms_product_reviews WHERE product_id IN %s", (tuple(all_ids),))
    print(f"  删除评论: {cur.rowcount} 条")

    # 订单商品项
    cur.execute("DELETE FROM oms_order_items WHERE product_id IN %s", (tuple(all_ids),))
    print(f"  删除订单项: {cur.rowcount} 条")

    # 购物车
    cur.execute("DELETE FROM oms_cart_items WHERE product_id IN %s", (tuple(all_ids),))
    print(f"  删除购物车: {cur.rowcount} 条")

    # SKU
    cur.execute("DELETE FROM pms_skus WHERE product_id IN %s", (tuple(all_ids),))
    print(f"  删除SKU: {cur.rowcount} 条")

    # 商品属性值
    cur.execute("DELETE FROM pms_product_attribute_values WHERE product_id IN %s", (tuple(all_ids),))
    print(f"  删除商品属性值: {cur.rowcount} 条")

    # 商品
    cur.execute("DELETE FROM pms_products WHERE id IN %s", (tuple(all_ids),))
    print(f"  删除商品: {cur.rowcount} 条")

    conn.commit()
    print("清理完成")

except Exception as e:
    conn.rollback()
    print(f"错误: {e}")
    raise
finally:
    cur.close()
    conn.close()
