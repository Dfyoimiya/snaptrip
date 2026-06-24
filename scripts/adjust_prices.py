import json
import requests
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

API_BASE = "http://localhost:8080/api/v1"
ADMIN_EMAIL = "admin@snaptrip.com"
ADMIN_PASSWORD = "admin123"

TARGET_CATEGORIES = {"文具办公", "母婴亲子", "健康保养", "农资园艺", "五金机电"}


def round_price(value: float) -> float:
    """Round to 2 decimal places"""
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(d)


def determine_price(name: str, category: str) -> tuple[float, float]:
    """Return (price, original_price) based on product name and category"""
    n = name.lower()

    # 文具办公
    if category == "文具办公":
        if "打印机" in name or "print" in n:
            if "佳能" in name and "mg2580" in n:
                price = 449.0
            elif "新北洋" in name or "rp80" in n:
                price = 389.0
            elif "佳能" in name:
                price = 480.0
            else:
                price = 500.0
        elif "白板笔" in name or "马克笔" in name:
            price = 29.9
        elif "温湿度计" in name or "温度计" in name:
            price = 39.9
        elif "打孔机" in name or "裁纸机" in name or "切纸机" in name:
            if "裁纸机" in name or "切纸机" in name:
                price = 229.0
            else:
                price = 129.0
        elif "夹子" in name or "燕尾夹" in name or "票夹" in name or "长尾夹" in name:
            if "24只" in name or "32mm" in name:
                price = 24.9
            else:
                price = 18.9
        elif name == "佳能":
            price = 450.0
        elif name == "得力":
            price = 88.0
        elif name == "新北洋":
            price = 350.0
        elif name == "齐心":
            price = 45.0
        else:
            price = 59.0

    # 母婴亲子
    elif category == "母婴亲子":
        if "奶粉" in name or "爱他美" in name:
            if "2段" in name or "800g" in name:
                price = 289.0
            else:
                price = 310.0
        elif "推车" in name or "婴儿车" in name:
            if "一键收车" in name or "四轮" in name:
                price = 459.0
            else:
                price = 389.0
        elif "变形车" in name or "遥控车" in name or "遥控汽车" in name:
            if "越野车" in name or "六驱" in name:
                price = 189.0
            else:
                price = 119.0
        elif "防晒帽" in name or "遮阳帽" in name:
            price = 59.0
        elif "积木" in name or "磁力" in name or "拼图" in name:
            price = 79.0
        elif "平衡车" in name or "滑步车" in name:
            price = 189.0
        elif "迪士尼" in name or "疯狂动物城" in name or "斜挎包" in name:
            price = 69.0
        elif name == "迪士尼":
            price = 85.0
        else:
            price = 99.0

    # 健康保养
    elif category == "健康保养":
        if "耳温枪" in name or "体温计" in name or "额温枪" in name:
            price = 99.0
        elif "气垫床" in name or "防褥疮" in name:
            price = 459.0
        elif "艾灸" in name or "艾草" in name or "熏蒸" in name:
            price = 89.0
        elif "燕窝" in name:
            if "干盏" in name or "100g" in name:
                price = 3200.0
            elif "蝶舞礼盒" in name or "40g" in name:
                price = 580.0
            else:
                price = 680.0
        elif "西洋参" in name or "花旗参" in name:
            if "100g" in name and "2" in name:
                price = 459.0
            else:
                price = 350.0
        elif "蜂蜜" in name or "康维他" in name or "麦卢卡" in name:
            price = 520.0
        elif "制氧机" in name or "吸氧机" in name or "氧气机" in name:
            if "5l" in n or "5L" in name:
                price = 1980.0
            else:
                price = 1500.0
        elif name == "海尔":
            price = 2100.0
        elif name == "康维他":
            price = 520.0
        elif name == "小仙炖":
            price = 650.0
        elif name == "雷允上":
            price = 420.0
        elif name == "可孚":
            price = 180.0
        elif "血压计" in name:
            price = 180.0
        else:
            price = 280.0

    # 农资园艺
    elif category == "农资园艺":
        if "篷布" in name or "帆布" in name or "遮阳" in name or "遮雨" in name:
            price = 109.0
        elif "花瓶" in name or "陶瓷" in name or "花艺" in name:
            price = 89.0
        elif "盆栽" in name or "发财树" in name or "鸭脚木" in name or "植物" in name:
            if "1.4" in name or "1.6" in name or "1.4-1.6" in name:
                price = 219.0
            else:
                price = 129.0
        elif "修枝剪" in name or "剪刀" in name or "果树枝" in name:
            if "强力版" in name or "2.0AH" in name or "无刷电机" in name:
                price = 549.0
            else:
                price = 389.0
        elif "柚子叶" in name or "碌柚叶" in name:
            if "顺丰" in name:
                price = 39.0
            else:
                price = 29.0
        else:
            price = 89.0

    # 五金机电
    elif category == "五金机电":
        if "割草机" in name or "打草机" in name:
            if "双电" in name or "20v" in n or "4.0ah" in n:
                price = 1199.0
            else:
                price = 899.0
        elif "工具箱" in name or "套装" in name or "组套" in name:
            if "65件" in name or ("德力西" in name and "套装" in name):
                price = 329.0
            elif "绿林" in name or "能工box" in n or "电动螺丝刀" in name:
                price = 369.0
            elif "清灰套装" in name or "螺丝刀" in name:
                price = 79.0
            else:
                price = 280.0
        elif "手拉车" in name or "购物车" in name or "小推车" in name:
            price = 89.0
        elif "卷尺" in name or "钢尺" in name or "尺子" in name:
            price = 29.9
        elif "电池" in name or "内阻仪" in name or "检测仪" in name or "电压" in name:
            price = 219.0
        elif "风扇" in name or "吹风机" in name or "鼓风机" in name or "除尘器" in name or "吹雪机" in name:
            if "裸机" in name:
                price = 219.0
            else:
                price = 299.0
        elif name == "得力":
            price = 150.0
        elif name == "德力西":
            price = 280.0
        elif name == "东成":
            price = 1100.0
        elif name == "威克士":
            price = 280.0
        elif name == "绿林":
            price = 350.0
        elif name == "阿蒂亚":
            price = 85.0
        elif name == "FNIRSI" or name == "菲尼瑞斯":
            price = 220.0
        else:
            price = 180.0
    else:
        price = 99.0

    # Compute original_price as ~1.25x price (with some rounding)
    original_price = round(price * 1.25)
    # Round to nice numbers
    if original_price > 1000:
        original_price = round(original_price / 100) * 100
    elif original_price > 100:
        original_price = round(original_price / 10) * 10
    elif original_price > 50:
        original_price = round(original_price / 5) * 5

    price = round_price(price)
    original_price = round_price(original_price)
    return price, original_price


def login() -> Optional[str]:
    """Login and return admin token"""
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["access_token"]
        else:
            print(f"Login failed: {data}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None


def get_product_detail(product_id: str, token: str) -> Optional[dict]:
    """Get product detail including SKUs"""
    try:
        resp = requests.get(
            f"{API_BASE}/admin/products/{product_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data")
        else:
            print(f"  Get detail failed: {data}")
            return None
    except Exception as e:
        print(f"  Get detail error: {e}")
        return None


def update_product(product_id: str, price: float, original_price: float, token: str) -> bool:
    """Update product price and original_price"""
    try:
        # Try PUT first (actual backend endpoint), fallback to PATCH if needed
        for method in ["put", "patch"]:
            try:
                resp = requests.request(
                    method,
                    f"{API_BASE}/admin/products/{product_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"price": price, "original_price": original_price},
                    timeout=10,
                )
                if resp.status_code == 405:
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 0:
                    return True
                else:
                    print(f"  Update product failed: {data}")
                    return False
            except requests.exceptions.HTTPError:
                if resp.status_code == 405:
                    continue
                raise
        return False
    except Exception as e:
        print(f"  Update product error: {e}")
        return False


def update_sku(product_id: str, sku_id: str, price: float, token: str) -> bool:
    """Update SKU price and promotion_price"""
    try:
        resp = requests.put(
            f"{API_BASE}/admin/products/{product_id}/skus/{sku_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"price": price, "promotion_price": price},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return True
        else:
            print(f"  Update SKU failed: {data}")
            return False
    except Exception as e:
        print(f"  Update SKU error: {e}")
        return False


def main():
    # 1. Read products
    with open("products_for_pricing.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    # 2. Filter
    filtered = [p for p in products if p["category"] in TARGET_CATEGORIES]
    print(f"Total products: {len(products)}")
    print(f"Filtered products in target categories: {len(filtered)}")
    print()

    if not filtered:
        print("No products to update.")
        return

    # 3. Determine prices
    updates = []
    for p in filtered:
        new_price, new_original = determine_price(p["name"], p["category"])
        updates.append({
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "old_price": p["price"],
            "old_original": p["original_price"],
            "new_price": new_price,
            "new_original": new_original,
        })

    # 4. Login
    token = login()
    if not token:
        print("Failed to login. Exiting.")
        return
    print("Login successful.")
    print()

    # 5. Update products and SKUs
    print("=" * 80)
    print("Price Adjustment Report")
    print("=" * 80)

    category_stats = {}

    for item in updates:
        cat = item["category"]
        if cat not in category_stats:
            category_stats[cat] = []

        print(f"\n【{item['category']}】{item['name']}")
        print(f"  ID: {item['id']}")
        print(f"  Price: {item['old_price']:.2f} -> {item['new_price']:.2f}")
        print(f"  Original: {item['old_original']:.2f} -> {item['new_original']:.2f}")

        # Update product
        ok = update_product(item["id"], item["new_price"], item["new_original"], token)
        if ok:
            print(f"  Product update: OK")
        else:
            print(f"  Product update: FAILED")
            continue

        # Get detail for SKUs
        detail = get_product_detail(item["id"], token)
        skus = detail.get("skus", []) if detail else []
        if skus:
            for sku in skus:
                sku_id = sku.get("id")
                old_sku_price = sku.get("price")
                if sku_id:
                    sku_ok = update_sku(item["id"], sku_id, item["new_price"], token)
                    print(f"  SKU {sku_id[:8]}... price {old_sku_price} -> {item['new_price']:.2f}: {'OK' if sku_ok else 'FAILED'}")
        else:
            print(f"  No SKUs found.")

        category_stats[cat].append({
            "price": item["new_price"],
            "original": item["new_original"],
        })

    # 6. Summary
    print()
    print("=" * 80)
    print("Category Price Summary")
    print("=" * 80)
    for cat, stats in sorted(category_stats.items()):
        if not stats:
            continue
        prices = [s["price"] for s in stats]
        print(f"\n{cat}:")
        print(f"  Count: {len(stats)}")
        print(f"  Price Range: {min(prices):.2f} - {max(prices):.2f}")
        print(f"  Price Average: {sum(prices)/len(prices):.2f}")


if __name__ == "__main__":
    main()
