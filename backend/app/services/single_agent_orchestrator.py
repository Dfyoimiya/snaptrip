"""Single-Agent Orchestrator —— LLM 决策 + ExecutionEngine 执行的编排循环。

职责:
  1. LLM 通过 function-calling 生成 AgentPlan
  2. PlanDraftValidator 确定性校验
  3. ExecutionEngine 安全执行
  4. 失败反馈 → LLM 重新规划（最多 MAX_PLAN_ITERATIONS 轮）
  5. 超过上限 → 降级响应

迭代上限:
  MAX_PLAN_ITERATIONS = 3    # 最多 3 轮 规划→执行→反馈 循环
  MAX_VALIDATION_RETRIES = 2 # 校验失败最多重试 2 次（之后放弃 LLM）

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.schemas.plan import AgentPlan, ExecutionResult
from app.services.plan_validator import PlanDraftValidator, ValidationError

logger = logging.getLogger(__name__)

# 迭代上限
MAX_PLAN_ITERATIONS = 3
MAX_VALIDATION_RETRIES = 2


# ------------------------------------------------------------------
# Protocols / Interfaces
# ------------------------------------------------------------------


class PlanGeneratorPort(Protocol):
    """LLM Plan Draft 生成接口（Protocol，方便测试 mock）。"""

    async def generate_plan(
        self,
        user_query: str,
        user_context: dict[str, Any],
        validation_errors: list[ValidationError] | None = None,
        execution_feedback: dict[str, Any] | None = None,
    ) -> AgentPlan: ...


class ExecutionEnginePort(Protocol):
    """ExecutionEngine 执行接口（Protocol）。"""

    async def execute(self, plan: AgentPlan, user_context: dict[str, Any]) -> ExecutionResult: ...


# ------------------------------------------------------------------
# Response types
# ------------------------------------------------------------------


@dataclass
class OrchestratorResponse:
    """编排器最终响应"""

    status: str  # "success" | "partial_success" | "max_retries_exceeded" | "validation_failed"
    execution_result: ExecutionResult | None = None
    message: str = ""
    validation_errors: list[ValidationError] = field(default_factory=list)


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------


class SingleAgentOrchestrator:
    """单 Agent 编排器 —— LLM 生成计划 + ExecutionEngine 安全执行。

    流程:
      1. LLM.generate_plan(user_query) → AgentPlan
      2. PlanDraftValidator.validate(plan) → ValidationResult
      3. 校验失败 → 回传 errors 给 LLM 重试（最多 MAX_VALIDATION_RETRIES 次）
      4. ExecutionEngine.execute(plan) → ExecutionResult
      5. 部分失败 → 回传 feedback 给 LLM 重试（最多 MAX_PLAN_ITERATIONS 次）
      6. 超过上限 → 降级响应
    """

    def __init__(
        self,
        plan_generator: PlanGeneratorPort,
        validator: PlanDraftValidator,
        execution_engine: ExecutionEnginePort,
    ) -> None:
        self._llm = plan_generator
        self._validator = validator
        self._engine = execution_engine
        self._last_validation_errors: list[ValidationError] | None = None

    async def run(self, user_query: str, user_context: dict[str, Any] | None = None) -> OrchestratorResponse:
        """执行完整的 规划→校验→执行 循环。

        Args:
            user_query: 用户原始查询
            user_context: 用户上下文（lat/lng, user_id, session_id 等）

        Returns:
            OrchestratorResponse
        """
        ctx = user_context or {}
        validation_failures = 0
        iteration = 0
        last_execution: ExecutionResult | None = None

        while iteration < MAX_PLAN_ITERATIONS:
            # ---- Step 1: LLM 生成 Plan Draft ----
            try:
                plan = await self._llm.generate_plan(
                    user_query=user_query,
                    user_context=ctx,
                    validation_errors=(self._last_validation_errors if validation_failures > 0 else None),
                    execution_feedback=(
                        _execution_to_feedback(last_execution)
                        if last_execution and last_execution.status != "full_success"
                        else None
                    ),
                )
            except Exception as e:
                logger.exception("llm_plan_generation_failed")
                return OrchestratorResponse(
                    status="validation_failed",
                    message=f"LLM 计划生成异常: {e}",
                )

            # ---- Step 2: 确定性校验 ----
            validation = self._validator.validate(plan)
            if not validation.valid:
                validation_failures += 1
                logger.warning(
                    "plan_validation_failed attempt=%d errors=%d",
                    validation_failures,
                    len(validation.errors),
                )
                self._last_validation_errors = validation.errors

                if validation_failures >= MAX_VALIDATION_RETRIES:
                    return OrchestratorResponse(
                        status="validation_failed",
                        message="Plan Draft 连续校验失败，已放弃 LLM 生成",
                        validation_errors=validation.errors,
                    )
                # 回传错误让 LLM 修正，不消耗执行迭代
                ctx = _with_validation_errors(ctx, validation.errors)
                continue

            validation_failures = 0

            # ---- Step 3: ExecutionEngine 执行 ----
            try:
                last_execution = await self._engine.execute(plan, ctx)
            except Exception:
                logger.exception("execution_engine_failed")
                iteration += 1
                continue

            if last_execution.status == "full_success":
                return OrchestratorResponse(
                    status="success",
                    execution_result=last_execution,
                    message="计划执行成功",
                )

            # ---- Step 4: 部分失败 → 下一轮 ----
            iteration += 1
            ctx = _with_execution_feedback(ctx, last_execution)
            logger.info(
                "orchestrator_retry iteration=%d status=%s",
                iteration,
                last_execution.status,
            )

        # ---- Step 5: 超过最大迭代 ----
        return OrchestratorResponse(
            status="max_retries_exceeded",
            execution_result=last_execution,
            message=(f"当前需求暂时无法自动完成（已尝试 {MAX_PLAN_ITERATIONS} 轮规划），已转人工客服"),
        )


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _with_validation_errors(ctx: dict[str, Any], errors: list[ValidationError]) -> dict[str, Any]:
    """将校验错误注入上下文，供 LLM 下一轮修正。"""
    return {
        **ctx,
        "validation_errors": [{"step_index": e.step_index, "code": e.code, "message": e.message} for e in errors],
    }


def _execution_to_feedback(result: ExecutionResult) -> dict[str, Any]:
    """将执行结果转为 LLM 可理解的反馈。"""
    return {
        "status": result.status,
        "failed_slots": [
            {
                "slot_index": f.slot_index,
                "tool_name": f.tool_name,
                "error_code": f.error_code,
                "error_message": f.error_message,
            }
            for f in result.failed_slots
        ],
        "confirmed_bookings": result.confirmed_bookings,
    }


def _with_execution_feedback(ctx: dict[str, Any], result: ExecutionResult) -> dict[str, Any]:
    """将执行反馈注入上下文。"""
    return {**ctx, "execution_feedback": _execution_to_feedback(result)}
