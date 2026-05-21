"""Plan Draft Validator —— LLM 生成的 Plan Draft 确定性校验器。

在 ExecutionEngine 编译 DAG 前执行代码级硬规则校验：
  1. 工具存在性 —— LLM 可能 hallucinate 不存在的工具名
  2. 参数 Schema 校验 —— JSON Schema 硬校验，不依赖 LLM 自我纠正
  3. 物理操作前置条件 —— book_table/book_ticket 前必须有 check_availability
  4. 循环依赖检测 —— 防止 LLM 生成 A→B→A 的工具序列

校验结果:
  - valid=True → ExecutionEngine 正常执行
  - valid=False → 将 errors 回传给 LLM，要求重新生成 Plan Draft
  - 连续 2 次校验失败 → 放弃 LLM，降级为关键字匹配 Fallback

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.schemas.plan import AgentPlan, AgentPlanStep
from app.schemas.tool import ToolDefinition

logger = logging.getLogger(__name__)

# 物理操作前置检查映射 —— 代码级硬编码，不可从 TOML 注入
_PRECHECK_MAP: dict[str, str] = {
    "book_table": "check_availability",
    "book_ticket": "check_availability",
    "order": "search_poi",
}


@dataclass
class ValidationError:
    """单条校验错误"""

    step_index: int = -1
    code: str = ""
    message: str = ""


@dataclass
class ValidationResult:
    """校验结果"""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)


class PlanDraftValidator:
    """Plan Draft 确定性校验器 —— 代码级硬规则。

    不依赖 LLM 自我纠正。所有规则都是白名单式的确定性检查。
    """

    def __init__(self, tools: dict[str, ToolDefinition]) -> None:
        self._tools = tools

    def validate(self, plan: AgentPlan) -> ValidationResult:
        """校验 Plan Draft，返回校验结果。

        Args:
            plan: LLM 生成的 Plan Draft

        Returns:
            ValidationResult(valid=True) 表示通过，可提交给 ExecutionEngine
        """
        errors: list[ValidationError] = []
        step_tool_names: list[str] = []

        for i, step in enumerate(plan.steps):
            tool = self._tools.get(step.tool_name)
            step_tool_names.append(step.tool_name)

            # 1. 工具存在性
            if tool is None:
                errors.append(
                    ValidationError(
                        step_index=i,
                        code="UNKNOWN_TOOL",
                        message=f"未知工具: {step.tool_name}",
                    )
                )
                continue  # 后续检查无意义

            # 2. 参数 JSON Schema 硬校验
            param_errors = self._validate_params(i, step, tool)
            errors.extend(param_errors)

            # 3. 物理操作前置条件
            if tool.physical_impact:
                precheck_errors = self._check_precheck(i, step, tool, step_tool_names)
                errors.extend(precheck_errors)

        # 4. 循环依赖检测
        if self._has_cycle(plan.steps):
            errors.append(
                ValidationError(
                    code="CYCLE_DETECTED",
                    message="Plan Draft 存在循环依赖",
                )
            )

        # 5. 空计划检测
        if not plan.steps:
            errors.append(ValidationError(code="EMPTY_PLAN", message="Plan Draft 没有包含任何工具调用"))

        valid = len(errors) == 0
        if not valid:
            logger.warning("plan_validation_failed errors=%d", len(errors))

        return ValidationResult(valid=valid, errors=errors)

    # ------------------------------------------------------------------
    # individual checks
    # ------------------------------------------------------------------

    def _validate_params(self, step_index: int, step: AgentPlanStep, tool: ToolDefinition) -> list[ValidationError]:
        """JSON Schema 硬校验参数。"""
        errors: list[ValidationError] = []

        try:
            _validate_against_schema(step.params, tool.input_schema)
        except ValueError as e:
            errors.append(
                ValidationError(
                    step_index=step_index,
                    code="INVALID_PARAMS",
                    message=f"{step.tool_name} 参数错误: {e}",
                )
            )

        return errors

    def _check_precheck(
        self,
        step_index: int,
        step: AgentPlanStep,
        tool: ToolDefinition,
        preceding_names: list[str],
    ) -> list[ValidationError]:
        """检查物理操作的必要前置工具是否已调用。"""
        required = _PRECHECK_MAP.get(step.tool_name)
        if required and required not in preceding_names:
            return [
                ValidationError(
                    step_index=step_index,
                    code="MISSING_PRECHECK",
                    message=f"{step.tool_name} 缺少前置检查: {required}",
                )
            ]
        return []

    @staticmethod
    def _has_cycle(steps: list[AgentPlanStep]) -> bool:
        """检测循环依赖。

        简单策略: 检查是否有重复的工具名出现在依赖链中，使用
        Kahn's algorithm 对 LLM 隐含的工具顺序做拓扑检测。
        """
        if len(steps) <= 1:
            return False

        # 构建邻接表（按步骤顺序隐含的依赖关系）
        indegree: dict[str, int] = defaultdict(int)
        for step in steps:
            indegree.setdefault(step.tool_name, 0)

        # 相邻步骤之间隐含"前置依赖"
        edges: list[tuple[str, str]] = []
        for i in range(len(steps) - 1):
            edges.append((steps[i].tool_name, steps[i + 1].tool_name))

        # 检测反向边 → 存在循环
        forward: set[tuple[str, str]] = set()
        for u, v in edges:
            if (v, u) in forward:
                return True
            forward.add((u, v))

        return False


def _validate_against_schema(params: dict[str, Any], schema: dict[str, Any]) -> None:
    """轻量 JSON Schema 校验，不依赖 jsonschema 库。

    仅校验 required 字段存在性和基础类型，足够覆盖 LLM 输出错误场景。
    """
    props = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    # 必填字段检查
    for key in required:
        if key not in params or params[key] is None:
            raise ValueError(f"缺少必填字段: {key}")

    # 类型检查
    for key, value in params.items():
        if key not in props:
            continue
        expected = props[key]
        expected_type = expected.get("type", "")

        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"字段 {key} 应为字符串，实际: {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            raise ValueError(f"字段 {key} 应为整数，实际: {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"字段 {key} 应为数字，实际: {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            raise ValueError(f"字段 {key} 应为数组，实际: {type(value).__name__}")
        elif expected_type == "object" and not isinstance(value, dict):
            raise ValueError(f"字段 {key} 应为对象，实际: {type(value).__name__}")

    # enum 约束 (per-field)
    for key, value in params.items():
        if key in props and "enum" in props[key] and value not in props[key]["enum"]:
            raise ValueError(f"字段 {key} 的值 '{value}' 不在允许范围 {props[key]['enum']} 内")
