#!/usr/bin/env python3
"""为每个商品设置相对真实的销量和库存。"""

import json
import random
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


# 分类销量范围：(最小销量, 最大销量, 库存倍数范围)
CATEGORY_CONFIG = {
    "数码产品": (50, 500, (1.5, 4.0)),      # 手机/笔记本销量中等，配件销量高
    "服饰鞋包": (30, 400, (2.0, 5.0)),      # 季节性销量差异大
    "户外运动": (20, 300, (1.5, 3.5)),      # 运动器材销量较低
    "个人美妆": (80, 600, (1.5, 3.5)),      # 化妆品复购率高
    "家具建材": (10, 150, (2.0, 5.0)),      # 大件低频购买
    "健康保养": (30, 250, (2.0, 4.0)),       # 保健品/医疗器械
    "文具办公": (50, 400, (2.0, 5.0)),       # 办公用品批量采购
    "五金机电": (20, 200, (2.0, 4.0)),       # 工具类
    "母婴亲子": (40, 300, (2.0, 4.0)),       # 母婴用品
    "汽车服务": (5, 100, (2.0, 5.0)),        # 汽车配件/服务低频
    "粮油调味": (150, 800, (2.0, 4.0)),      # 快消食品销量高
    "食品酒饮": (100, 600, (2.0, 4.0)),       # 零食饮料复购
    "农资园艺": (15, 150, (2.5, 5.0)),        # 农资低频
    "家用电器": (20, 200, (1.5, 3.5)),       # 大家电低频
    "萌宠护理": (40, 350, (2.0, 4.0)),        # 宠物用品
}

# 价格修正系数（价格越高，销量通常越低）
PRICE_FACTORS = [
    (0, 50, 1.5),       # 低价商品销量高
    (50, 200, 1.2),
    (200, 1000, 1.0),   # 中等价格正常
    (1000, 3000, 0.7),  # 高价销量降低
    (3000, 10000, 0.4), # 高价销量更低
    (10000, float('inf'), 0.2),  # 超高价销量很低
]


def generate_sales_and_stock(price, category_name):
    """基于价格和分类生成合理的销量和库存。"""
    config = CATEGORY_CONFIG.get(category_name, (20, 200, (2.0, 4.0)))
    min_sales, max_sales, stock_range = config
    
    # 价格修正
    price_factor = 1.0
    for min_p, max_p, factor in PRICE_FACTORS:
        if min_p <= price < max_p:
            price_factor = factor
            break
    
    # 生成销量（基础销量 * 价格修正）
    base_sales = random.randint(min_sales, max_sales)
    sales = int(base_sales * price_factor)
    sales = max(5, sales)  # 至少5个销量
    
    # 生成库存（基于销量的倍数）
    stock_multiplier = random.uniform(stock_range[0], stock_range[1])
    stock = int(sales * stock_multiplier)
    stock = max(10, stock)  # 至少10个库存
    
    # 添加随机波动
    sales = int(sales * random.uniform(0.8, 1.2))
    stock = int(stock * random.uniform(0.9, 1.1))
    
    return sales, stock


def update_product_stock(token, product_id, stock, sale_count):
    """更新商品库存和销量。"""
    payload = {"stock": stock, "sale_count": sale_count}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "PUT", f"/api/v1/admin/products/{product_id}",
        headers=headers, data=json.dumps(payload).encode()
    )
    return result.get("code") == 0


def update_sku_stock(token, product_id, sku_id, stock):
    """更新 SKU 库存。"""
    payload = {"stock": stock}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "PUT", f"/api/v1/admin/products/{product_id}/skus/{sku_id}",
        headers=headers, data=json.dumps(payload).encode()
    )
    return result.get("code") == 0


def main():
    # 从数据库获取所有导入商品
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.price, c.name as category_name
        FROM pms_products p
        LEFT JOIN pms_categories c ON p.category_id = c.id
        WHERE p.created_at > '2026-06-23 20:00:00'
        ORDER BY c.name, p.name
    """)
    products = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"找到 {len(products)} 个导入商品")
    
    token = login()
    print(f"登录成功\n")
    
    success = 0
    failed = 0
    
    for idx, (pid, name, price, cat_name) in enumerate(products, 1):
        sales, stock = generate_sales_and_stock(float(price), cat_name)
        
        print(f"[{idx}/{len(products)}] {name[:50]}... | price={price} | sales={sales} | stock={stock}")
        
        if update_product_stock(token, pid, stock, sales):
            # 更新 SKU 库存（与商品相同）
            result = _make_request(
                "GET", f"/api/v1/admin/products/{pid}",
                headers={"Authorization": f"Bearer {token}"}
            )
            skus = result.get("data", {}).get("skus", []) if result.get("code") == 0 else []
            for sku in skus:
                update_sku_stock(token, pid, sku["id"], stock)
            success += 1
        else:
            print(f"  ❌ 更新失败")
            failed += 1
    
    print(f"\n完成: 成功 {success}, 失败 {failed}, 总计 {len(products)}")
    
    # 汇总
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, 
               COUNT(*) as cnt,
               MIN(p.sale_count) as min_sales,
               MAX(p.sale_count) as max_sales,
               ROUND(AVG(p.sale_count), 0) as avg_sales,
               MIN(p.stock) as min_stock,
               MAX(p.stock) as max_stock,
               ROUND(AVG(p.stock), 0) as avg_stock
        FROM pms_products p
        LEFT JOIN pms_categories c ON p.category_id = c.id
        WHERE p.created_at > '2026-06-23 20:00:00'
        GROUP BY c.name
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n分类汇总:")
    print(f"{'分类':<12} {'数量':<5} {'销量范围':<20} {'平均销量':<10} {'库存范围':<20} {'平均库存':<10}")
    print("-" * 80)
    for r in rows:
        print(f"{r[0]:<12} {r[1]:<5} {r[2]}-{r[3]:<15} {r[4]:<10} {r[5]}-{r[6]:<15} {r[7]:<10}")


if __name__ == "__main__":
    main()
