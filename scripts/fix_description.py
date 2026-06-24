#!/usr/bin/env python3
"""修复商品 description：从 HTML 图片 blob 替换为纯文本描述。"""

import psycopg2
import re

# 描述模板（按分类）
CATEGORY_TEMPLATES = {
    "数码产品": "{name}，精选品质，性能出众，为您带来卓越的使用体验。",
    "服饰鞋包": "{name}，时尚设计，舒适贴身，展现您的独特品味。",
    "食品酒饮": "{name}，精选原料，品质保证，美味健康，值得品尝。",
    "个人美妆": "{name}，优质配方，精心呵护，让您的美丽更自信。",
    "五金机电": "{name}，坚固耐用，精工品质，是家庭和工作的得力助手。",
    "健康保养": "{name}，关注健康，品质保障，为您和家人的健康保驾护航。",
    "文具办公": "{name}，实用设计，高效办公，学习和工作的最佳伴侣。",
    "母婴亲子": "{name}，安全材质，贴心设计，给宝宝最好的呵护。",
    "农资园艺": "{name}，优质选材，耐用实用，让您的园艺生活更轻松。",
    "汽车服务": "{name}，专业品质，安全可靠，为您的爱车提供最佳服务。",
    "粮油调味": "{name}，精选原料，品质保证，美味健康，值得品尝。",
    "萌宠护理": "{name}，温和配方，安全无害，给您的宠物最好的呵护。",
    "户外运动": "{name}，专业设计，品质保障，让您尽享运动乐趣。",
    "家具建材": "{name}，品质材料，精致工艺，打造温馨舒适的家居环境。",
    "家用电器": "{name}，智能便捷，品质可靠，让生活更加舒适美好。",
}

DEFAULT_TEMPLATE = "{name}，品质优良，值得信赖，为您的生活增添便利。"


def generate_description(name: str, category_name: str) -> str:
    """基于商品名称和分类生成纯文本描述。"""
    template = CATEGORY_TEMPLATES.get(category_name, DEFAULT_TEMPLATE)
    # 清理名称中的京东后缀
    clean_name = re.sub(r'【行情 报价 价格 评测】-京东$', '', name).strip()
    clean_name = re.sub(r'【行情 报价 价格 评测】$', '', clean_name).strip()
    return template.format(name=clean_name)


def main():
    conn = psycopg2.connect(
        host="localhost", port=5432, database="snaptrip_dev",
        user="snaptrip", password="snaptrip_dev_pass"
    )
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 获取所有导入商品
        cur.execute("""
            SELECT p.id, p.name, c.name as category_name
            FROM pms_products p
            LEFT JOIN pms_categories c ON p.category_id = c.id
            WHERE p.created_at > '2026-06-23 20:00:00'
        """)
        products = cur.fetchall()
        print(f"找到 {len(products)} 个导入商品")

        updated = 0
        for pid, name, cat_name in products:
            desc = generate_description(name, cat_name or "")
            cur.execute(
                "UPDATE pms_products SET description = %s WHERE id = %s",
                (desc, pid)
            )
            updated += 1

        conn.commit()
        print(f"更新完成：{updated} 个商品的 description 已替换为纯文本")

        # 验证
        cur.execute("""
            SELECT id, name, description FROM pms_products
            WHERE created_at > '2026-06-23 20:00:00' LIMIT 5
        """)
        print("\n示例：")
        for row in cur.fetchall():
            print(f"  {row[1][:40]}... | {row[2][:60]}")

    except Exception as e:
        conn.rollback()
        print(f"错误: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
