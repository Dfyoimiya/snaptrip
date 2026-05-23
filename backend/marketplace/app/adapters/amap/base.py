"""AmapAdapter 抽象基类 —— 对接到现有 Tool 协议。

每个 Adapter 实现:
- tool_name: 对应 TOOL_REGISTRY 中的工具名
- execute(invocation) → ToolResult: 统一入口
- validate(params) → bool: 参数校验

设计原则 (SOCID - Interface Segregation):
  BaseAmapAdapter 仅定义 execute() 一个核心方法，
  不强制子类实现不需要的接口。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from agent.schemas.tool import ToolInvocation, ToolResult


class BaseAmapAdapter(ABC):
    """高德 API 适配器抽象基类。

    子类必须:
    1. 设置 tool_name 类属性
    2. 实现 async _call_api(params) → dict 方法
    """

    tool_name: str = ""

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """统一执行入口 —— 自动计时的安全调用。

        Args:
            invocation: Tool 调用请求

        Returns:
            ToolResult 含 status / data / latency_ms
        """
        t0 = time.perf_counter()
        try:
            if not await self.validate(invocation.params):
                elapsed = int((time.perf_counter() - t0) * 1000)
                return ToolResult(
                    invocation_id=invocation.invocation_id,
                    status="failure",
                    error_code="INVALID_PARAMS",
                    error_message=f"参数校验失败: {invocation.params}",
                    latency_ms=elapsed,
                )

            data = await self._call_api(invocation.params)
            elapsed = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                invocation_id=invocation.invocation_id,
                status="success",
                data=data,
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                invocation_id=invocation.invocation_id,
                status="failure",
                error_code=type(e).__name__.upper(),
                error_message=str(e),
                latency_ms=elapsed,
            )

    async def validate(self, params: dict) -> bool:
        """参数校验 —— 子类可覆盖以添加自定义校验。

        Args:
            params: 工具调用参数

        Returns:
            True 表示参数合法
        """
        return True

    @abstractmethod
    async def _call_api(self, params: dict) -> dict:
        """调用高德 API 并返回原始数据 —— 子类实现核心业务逻辑。

        Args:
            params: 工具调用参数

        Returns:
            dict: API 返回的原始数据（后续由 Mapper 转换为内部 Schema）
        """
        ...
