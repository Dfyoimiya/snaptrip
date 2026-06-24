"""展示层工具函数 — 用于格式化商品/订单等数据的展示文本。

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations


def format_sale_count(sale_count: int | None) -> str:
    """格式化销量显示文本。

    规则:
      - 销量 < 100: 具体显示原始数字, e.g. "67"
      - 销量 >= 100: 向下取整到最近的整百/整千, e.g. 678 -> "600+", 2979 -> "2000+"
    """
    if sale_count is None:
        return "0"

    if sale_count < 100:
        return str(sale_count)

    if sale_count < 1000:
        # 100-999: 向下取整到整百
        return f"{(sale_count // 100) * 100}+"

    # >= 1000: 向下取整到整千
    return f"{(sale_count // 1000) * 1000}+"
