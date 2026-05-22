"""高德 API 通用类型 —— 处理高德返回 [] 代替 "" 的情况。

AmapStr: 自动将空数组 [] 转换为空字符串 "" 的 Annotated 类型。
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator


def _coerce_amap_str(v: Any) -> str:
    """高德 API 部分字段可能返回 [] (空数组) 或数字, 而非字符串, 统一转换。"""
    if isinstance(v, list):
        return ""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


AmapStr = Annotated[str, BeforeValidator(_coerce_amap_str)]
