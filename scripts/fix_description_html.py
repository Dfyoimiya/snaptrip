#!/usr/bin/env python3
"""修复商品 description：从纯文本恢复为包含 album_pics 图片的 HTML。"""

import psycopg2


def build_detail_html(album_pics: str, description_text: str) -> str:
    """将 album_pics 图片列表生成 HTML 详情内容。"""
    if not album_pics:
        return f"<p>{description_text}</p>"

    parts = [f"<p>{description_text}</p>"]
    for url in album_pics.split(','):
        url = url.strip()
        if url:
            parts.append(
                f'<p><img src="{url}" style="max-width:100%; display:block; margin-bottom:12px;" /></p>'
            )
    return "\n".join(parts)


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
            SELECT id, album_pics, description
            FROM pms_products
            WHERE created_at > '2026-06-23 20:00:00'
        """)
        products = cur.fetchall()
        print(f"找到 {len(products)} 个导入商品")

        updated = 0
        for pid, album_pics, desc_text in products:
            # 如果 description 是纯文本，用它来作为文字说明
            # 如果已经有 HTML，跳过
            if desc_text and '<img' in desc_text:
                continue

            html = build_detail_html(album_pics or '', desc_text or '')
            cur.execute(
                "UPDATE pms_products SET description = %s WHERE id = %s",
                (html, pid)
            )
            updated += 1

        conn.commit()
        print(f"更新完成：{updated} 个商品的 description 已恢复为 HTML")

        # 验证
        cur.execute("""
            SELECT id, name, description FROM pms_products
            WHERE created_at > '2026-06-23 20:00:00' LIMIT 3
        """)
        print("\n示例：")
        for row in cur.fetchall():
            print(f"  {row[1][:40]}...")
            print(f"  Desc: {row[2][:150]}...")
            print()

    except Exception as e:
        conn.rollback()
        print(f"错误: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
