"""Tool Definition Adapter —— 将 ToolRegistry 转为 LLM function-calling schema。

职责:
  - 过滤: 只暴露 LLM 需要的字段 (name, description, parameters)
  - 格式: 转为 OpenAI function-calling 格式
  - 净化: 防止 tools.toml 中的 llm_description 被 prompt 注入污染
  - 注入: 将工具描述注入到 LLM system prompt 或作为 functions 参数

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.schemas.tool import ToolDefinition

logger = logging.getLogger(__name__)

# 内置安全描述 —— TOML 描述被污染时使用的代码级硬编码后备
_BUILTIN_SAFE_DESCRIPTIONS: dict[str, str] = {
    "search_poi": "搜索指定城市内的兴趣点(POI)，支持按类别、坐标半径过滤。",
    "get_user_profile": "获取当前用户的偏好画像与历史行为向量。",
    "check_queue": "查询指定POI的当前排队人数和预计等待时间。",
    "check_availability": "查询指定POI在给定时间范围内是否有可用时段/座位/库存。",
    "check_child_facility": "查询指定POI的亲子友好设施。",
    "calculate_route": "计算两点之间的路线距离和通行时间。",
    "book_table": "预订指定餐厅的桌位。",
    "book_ticket": "预订景点或活动门票。",
    "order": "在指定POI下单点餐或购物。",
    "notify": "向用户发送计划确认通知和分享卡片。",
}


class ToolDefinitionAdapter:
    """将 ToolRegistry 转为 LLM function-calling schema。

    双重职责:
      1. 格式转换: ToolDefinition → OpenAI function-calling JSON
      2. 安全净化: 检测并拦截 tools.toml 中的 prompt 注入
    """

    # 可疑指令关键词/模式
    _FORBIDDEN_PATTERNS: list[str] = [
        r"\bignore\b",
        r"\boverride\b",
        r"\bbypass\b",
        r"\bdo\s*not\b",
        r"\bdont\b",
        r"\bnever\b",
        r"\bdisregard\b",
        r"跳过",
        r"忽略",
        r"无视",
        r"绕过",
        r"不要",
        # 企图覆盖 system prompt 的模式
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[system\]",
        r"\[/system\]",
        r"<system>",
        r"</system>",
        r"\[INST\]",
        r"\[/INST\]",
    ]

    def __init__(self, tools: dict[str, ToolDefinition]) -> None:
        self._tools = tools

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def to_openai_functions(self) -> list[dict[str, Any]]:
        """转为 OpenAI function-calling 格式。

        仅暴露 LLM 需要的字段: name, description, parameters
        不暴露: layer, dependencies, fallback_policy, is_idempotent, physical_impact
        """
        functions: list[dict[str, Any]] = []
        for name, tool in self._tools.items():
            safe_desc = self._sanitize_description(tool.llm_description or tool.description, name)
            functions.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": safe_desc,
                        "parameters": tool.input_schema,
                    },
                }
            )
        return functions

    def to_system_prompt_fragment(self) -> str:
        """生成可注入 system prompt 的工具描述文本。

        适用于不支持原生 function-calling 的模型。
        """
        lines = ["可用工具列表:", ""]
        for name, tool in self._tools.items():
            safe_desc = self._sanitize_description(tool.llm_description or tool.description, name)
            params_str = self._describe_params(tool.input_schema)
            lines.append(f"- {name}: {safe_desc}")
            if params_str:
                lines.append(f"  参数: {params_str}")
            lines.append("")
        return "\n".join(lines)

    def get_tool_metadata(self, tool_name: str) -> ToolDefinition | None:
        """获取单个工具的完整元数据（ExecutionEngine 使用）。"""
        return self._tools.get(tool_name)

    # ------------------------------------------------------------------
    # sanitization
    # ------------------------------------------------------------------

    def _sanitize_description(self, desc: str, tool_name: str) -> str:
        """净化工具描述，防止 prompt 注入。

        检测到可疑指令 → 记录告警 + 降级为内置安全描述。
        """
        if not desc:
            return _BUILTIN_SAFE_DESCRIPTIONS.get(tool_name, f"调用 {tool_name} 工具")

        for pattern in self._FORBIDDEN_PATTERNS:
            if re.search(pattern, desc, re.IGNORECASE):
                logger.warning(
                    "tool_description_suspicious tool=%s pattern=%r",
                    tool_name,
                    pattern,
                )
                return self._get_safe_fallback(tool_name)

        # 长度限制（防止超长 prompt 消耗 token）
        if len(desc) > 500:
            return desc[:500]
        return desc

    def _get_safe_fallback(self, tool_name: str) -> str:
        """返回内置安全描述 —— 硬编码于代码中，不可被 TOML 覆盖。"""
        return _BUILTIN_SAFE_DESCRIPTIONS.get(tool_name, f"调用 {tool_name} 工具")

    @staticmethod
    def _describe_params(schema: dict[str, Any]) -> str:
        """从 JSON Schema 提取参数描述。"""
        props = schema.get("properties", {})
        if not props:
            return ""
        required = schema.get("required", [])
        parts: list[str] = []
        for name, prop in props.items():
            desc = prop.get("description", "")
            req = "必填" if name in required else "可选"
            if desc:
                parts.append(f"{name}({req}, {desc})")
            else:
                parts.append(f"{name}({req})")
        return ", ".join(parts)
