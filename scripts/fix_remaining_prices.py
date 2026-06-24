#!/usr/bin/env python3
"""手动调整剩余未设置价格的商品。"""

import json
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


# 剩余未调整的商品价格（根据实际内容判断）
PRICE_MAP = {
    # 健康保养
    "可孚耳温枪精准温度计电子体温计宝宝体温枪婴儿额温枪老人HW-016": (89, 119),
    # 家用电器
    "Brateck北弧65-100吋电视移动支架可移动电视架落地艺术架电视支架移动电视柜现代_轻奢haven FS800MA": (459, 599),
    "KANGYAN【一级能效】双桶壁挂内衣洗衣机小型全自动高温煮洗烘脱一体内裤清洗机双仓舱专用洗袜子懒人神器 桌面款【洗烘一": (899, 1299),
    "芝杜（ZIDOO）Z9X8K 8KUHD杜比视界4KHDR全景声蓝光家庭影院高清硬盘播放器网络机顶盒无损音乐 Z9X8K": (3299, 3999),
    # 数码产品
    "HANUWEI新款512G大内存7800mAh快充大电池长续航骁龙8电竞新款手机 雪山白 16G+128GB": (899, 1299),
    "任天堂（Nintendo）【国内保税仓】Switch2_1代 OLED_续航加强日版_港版便携家用ns体感游戏机掌机 港": (2599, 3299),
    "大疆DJI Osmo Nano 标准套装（64GB）自由视角穿戴相机Vlog骑行亲子宠物运动相机4K拇指相机": (1999, 2499),
    "小米15 徕卡光学Summilux高速镜头 骁龙8至尊版移动平台 小米澎湃OS 2 12+512 白色 5g手机": (4999, 5999),
    "小米（MI）REDMI Watch 6皎月银 国家补贴 澎湃OS 3 心率血氧监测 红米手表6 小米汽车 送男友送女友": (499, 699),
    "小米空调 巨省电 新一级能效变频冷暖壁挂式卧室智能空调挂机30S速冷60S速热 智慧清洁 巨省电 1.5匹 宽温域运行A": (1999, 2499),
    "方正【国家补贴】笔记本电脑轻薄商务办公本学生专用15.6英寸高清屏256G容量游戏娱乐全能本": (2599, 3299),
    "机械革命极光X 2026 酷睿i7HX 游戏本笔记本电脑(i7-13645HX 16G 512G RTX5060 2.5K屏 180Hz 灰)": (6999, 8499),
    "漫步者花再Halo SoundBar桌面音响音箱家用台式电脑游戏音响长条有线音箱蓝牙RGB灯效高保真 破界黑": (399, 499),
    "罗技（G）GPW3 狗屁王三代gpw无线游戏鼠标 专业电竞手型 GPW2金刚升级款 三角洲_无畏契约 粉【全网爆款】": (799, 999),
    "美的505L十字门冰箱双系统双循环保鲜大容量三档变温一级能效风冷无霜MR-531WSPZE国家补贴": (3599, 4599),
    "荣耀笔记本 X14 2026 战斗版【国家补贴】高性能全新英特尔Core5 320 16G 512G 14吋护眼屏 持久": (3999, 4999),
    "西部数据（WD）SSD固态硬盘M.2接口 SN7100 PCIe4.0 笔记本台式机固态硬盘 AI电脑配件 SN7100": (599, 799),
}


def update_product(token, product_id, price, original_price):
    """更新商品价格。"""
    payload = {"price": price, "original_price": original_price}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    result = _make_request(
        "PUT", f"/api/v1/admin/products/{product_id}",
        headers=headers, data=json.dumps(payload).encode()
    )
    return result.get("code") == 0


def update_sku(token, product_id, sku_id, price):
    """更新 SKU 价格。"""
    payload = {
        "price": price,
        "promotion_price": round(price * 0.9, 2),
    }
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
    import psycopg2
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name
        FROM pms_products p
        WHERE p.created_at > '2026-06-23 20:00:00' AND p.price = 99.0
    """)
    products = cur.fetchall()
    cur.close()
    conn.close()

    print(f"找到 {len(products)} 个未调整商品")
    if not products:
        print("无需处理")
        return

    token = login()
    print(f"登录成功\n")

    success = 0
    failed = 0
    for pid, name in products:
        price, original = None, None
        for key, (p, op) in PRICE_MAP.items():
            if key in name or name.startswith(key[:20]):
                price, original = p, op
                break

        if price is None:
            print(f"  ⚠️ 未匹配价格: {name[:50]}")
            failed += 1
            continue

        print(f"[{success+failed+1}/{len(products)}] {name[:50]}")
        if update_product(token, pid, price, original):
            # 更新 SKU
            result = _make_request(
                "GET", f"/api/v1/admin/products/{pid}",
                headers={"Authorization": f"Bearer {token}"}
            )
            skus = result.get("data", {}).get("skus", []) if result.get("code") == 0 else []
            for sku in skus:
                update_sku(token, pid, sku["id"], price)
            print(f"  ✅ price={price}, original={original}")
            success += 1
        else:
            print(f"  ❌ 更新失败")
            failed += 1

    print(f"\n完成: 成功 {success}, 失败 {failed}, 总计 {len(products)}")


if __name__ == "__main__":
    main()
