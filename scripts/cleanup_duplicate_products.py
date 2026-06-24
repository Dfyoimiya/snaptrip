#!/usr/bin/env python3
"""删除重复商品，只保留每个名称+分类最新创建的一个。"""

import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, database="snaptrip_dev",
    user="snaptrip", password="snaptrip_dev_pass"
)
conn.autocommit = False
cur = conn.cursor()

try:
    # 找出所有重复商品（保留最新创建的一个）
    cur.execute('''
        SELECT id, name, category_id, created_at,
               ROW_NUMBER() OVER (PARTITION BY name, category_id ORDER BY created_at DESC) as rn
        FROM pms_products
        WHERE created_at > '2026-06-23 20:00:00'
    ''')
    all_rows = cur.fetchall()

    # 需要删除的重复商品ID
    dup_ids = [row[0] for row in all_rows if row[4] > 1]
    print(f"找到 {len(dup_ids)} 个重复商品需要删除")

    if not dup_ids:
        print("没有重复商品")
        conn.commit()
        exit(0)

    # 删除关联数据（按外键依赖顺序）
    # 评论
    cur.execute("DELETE FROM pms_product_reviews WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除评论: {cur.rowcount} 条")

    # 订单商品项
    cur.execute("DELETE FROM oms_order_items WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除订单项: {cur.rowcount} 条")

    # 购物车
    cur.execute("DELETE FROM oms_cart_items WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除购物车: {cur.rowcount} 条")

    # SKU
    cur.execute("DELETE FROM pms_skus WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除SKU: {cur.rowcount} 条")

    # 商品属性值
    cur.execute("DELETE FROM pms_product_attribute_values WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除商品属性值: {cur.rowcount} 条")

    # 商品向量/embedding
    cur.execute("DELETE FROM pms_product_cf_vectors WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除CF向量: {cur.rowcount} 条")
    cur.execute("DELETE FROM pms_product_embeddings WHERE product_id IN %s", (tuple(dup_ids),))
    print(f"  删除embedding: {cur.rowcount} 条")

    # 商品
    cur.execute("DELETE FROM pms_products WHERE id IN %s", (tuple(dup_ids),))
    print(f"  删除商品: {cur.rowcount} 条")

    conn.commit()
    print(f"\n清理完成，删除了 {len(dup_ids)} 个重复商品")

except Exception as e:
    conn.rollback()
    print(f"错误: {e}")
    raise
finally:
    cur.close()
    conn.close()
