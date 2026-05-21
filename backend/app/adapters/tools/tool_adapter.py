"""Tool Adapter —— 统一工具调用入口。

组合:
  - Provider: 单工具原子调用
  - Idempotency: 幂等性检查
  - CircuitBreaker: 双层熔断
  - ToolDefinitionPort: 向 LLM 暴露工具定义

ExecutionEngine 通过此 Adapter 调用工具，无需感知底层实现。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.tools.base import BaseToolProvider
from app.providers.tools.registry import ToolRegistry
from app.schemas.tool import ToolDefinition
from app.schemas.tool_provider import PhysicalActionState, ToolProviderConfig, ToolProviderResult
from app.services.idempotency import IdempotencyService, IdempotencyUnavailableError
from app.services.tool_definition_adapter import ToolDefinitionAdapter

logger = logging.getLogger(__name__)


class ToolAdapter:
    """统一工具 Adapter —— 实现 ToolDefinitionPort + 工具调用能力。

    职责:
      1. ToolDefinitionPort: 向 LLM 暴露工具定义
      2. 工具调用: 幂等检查 → Provider.call()
      3. 工具取消: Provider.cancel()
      4. 状态查询: Provider.query_status()

    ExecutionEngine 通过此 Adapter 间接调用 Provider，无需感知
    Idempotency / CircuitBreaker / Provider 的具体实现。
    """

    def __init__(
        self,
        provider: BaseToolProvider,
        registry: ToolRegistry,
        idempotency: IdempotencyService | None = None,
        existing_defs: dict[str, ToolDefinition] | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._idempotency = idempotency
        merged = registry.to_tool_definitions(existing_defs)
        self._definition_adapter = ToolDefinitionAdapter(merged)
        self._tool_definitions = merged

    # ------------------------------------------------------------------
    # ToolDefinitionPort
    # ------------------------------------------------------------------

    def get_function_definitions(self) -> list[dict[str, Any]]:
        """返回 OpenAI function-calling 格式的工具列表。"""
        return self._definition_adapter.to_openai_functions()

    def get_tool_metadata(self, tool_name: str) -> ToolDefinition | None:
        """获取单个工具的完整元数据（ExecutionEngine 使用）。"""
        return self._definition_adapter.get_tool_metadata(tool_name)

    # ------------------------------------------------------------------
    # tool invocation
    # ------------------------------------------------------------------

    async def call(
        self,
        tool_name: str,
        params: dict,
        idempotency_key: str | None = None,
    ) -> ToolProviderResult:
        """执行工具调用（含幂等检查）。

        Args:
            tool_name: 工具名
            params: 工具参数
            idempotency_key: 幂等键（None 表示跳过幂等检查）

        Returns:
            ToolProviderResult
        """
        cfg = self._registry.get(tool_name)

        # 1. 幂等检查
        if idempotency_key and self._idempotency and cfg:
            try:
                decision = await self._idempotency.acquire(idempotency_key, cfg)
            except IdempotencyUnavailableError:
                return ToolProviderResult(
                    status="failure",
                    error_code="IDEMPOTENCY_UNAVAILABLE",
                    error_message="幂等服务不可用，物理操作暂停",
                    retryable=True,
                )

            if decision.is_duplicate:
                logger.info("tool_idempotent_replay tool=%s key=%s", tool_name, idempotency_key)
                if decision.cached_result:
                    return ToolProviderResult(**decision.cached_result)
                return ToolProviderResult(
                    status="success",
                    data={"idempotent_replay": True},
                )

        # 2. Provider 调用
        try:
            result = await self._provider.call(
                tool_name=tool_name,
                params=params,
                idempotency_key=idempotency_key or "",
            )
        except Exception as e:
            logger.exception("tool_call_failed tool=%s", tool_name)
            return ToolProviderResult(
                status="failure",
                error_code="PROVIDER_ERROR",
                error_message=str(e),
            )

        # 3. 缓存幂等结果
        if idempotency_key and self._idempotency and result.status == "success":
            await self._idempotency.mark_completed(
                idempotency_key,
                result.model_dump(),
                ttl=cfg.idempotency_ttl_sec if cfg else None,
            )

        return result

    async def cancel(self, tool_name: str, booking_ref: str) -> ToolProviderResult:
        """取消预订/订单（Saga 补偿用）。"""
        try:
            return await self._provider.cancel(tool_name, booking_ref)
        except Exception as e:
            logger.exception("tool_cancel_failed tool=%s ref=%s", tool_name, booking_ref)
            return ToolProviderResult(
                status="failure",
                error_code="CANCEL_ERROR",
                error_message=str(e),
                physical_state=PhysicalActionState.UNKNOWN,
            )

    async def query_status(self, tool_name: str, booking_ref: str) -> PhysicalActionState:
        """查询物理操作状态（UNKNOWN 异步确认用）。"""
        try:
            return await self._provider.query_status(tool_name, booking_ref)
        except Exception as e:
            logger.warning(
                "tool_query_status_failed tool=%s ref=%s error=%s",
                tool_name,
                booking_ref,
                e,
            )
            return PhysicalActionState.UNKNOWN

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------

    @property
    def provider(self) -> BaseToolProvider:
        return self._provider

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def get_config(self, tool_name: str) -> ToolProviderConfig | None:
        return self._registry.get(tool_name)
