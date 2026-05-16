"""Agent 协议层 —— 基类抽象与通用上下文。

定义所有 Agent 必须遵循的接口契约：
- BaseAgent: 抽象基类，每个 Agent 继承并实现 execute() 方法
- AgentContext: 跨 Agent 共享的执行上下文，通过 history 链传递数据
- AgentResult: 统一的结果封装，含执行状态、数据、耗时

Agent 间通信采用内存 Schema 传递（非消息队列），理由：
- 9 个 Agent 在同一个 FastAPI 事件循环中运行
- 通过 Python async def 调用传递 Pydantic Schema 对象，避免序列化开销
- 仅 Execution Engine 调用 Mock API 时走 HTTP

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    """Agent 执行上下文。

    跨 Agent 共享的运行时数据容器，通过 history 链传递上游产出。
    每个 Agent 从 context.history 读取所需数据，执行后将 AgentResult 追加到 history。

    Attributes:
        plan_id: 计划唯一标识，自动生成
        session_id: 会话标识
        user_input: 用户原始自然语言输入
        lat/lng: 用户当前位置坐标
        state: 当前 FSM 状态
        history: Agent 执行结果列表，按执行顺序排列
    """
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = "default"
    user_input: str = ""
    lat: float = 39.9219
    lng: float = 116.4435
    state: str = "idle"
    history: list[AgentResult] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Agent 执行结果。

    统一封装每个 Agent 的执行产出，含状态、数据和性能指标。

    Attributes:
        agent_name: Agent 名称，由 BaseAgent._timed 自动填充
        status: 执行状态 (success/failed/timeout)
        data: 业务数据，各 Agent 按 Schema 填充
        error: 失败时的错误信息
        elapsed_ms: 执行耗时（毫秒）
    """
    agent_name: str = ""
    status: str = "success"
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: int = 0


class BaseAgent(ABC):
    """所有 Agent 的抽象基类。

    每个 Agent 必须：
    1. 设置 name 属性
    2. 实现 async def execute(self, context) -> AgentResult

    _timed 装饰器自动填充 agent_name 和 elapsed_ms。
    """
    name: str = "base"

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 Agent 核心逻辑。

        Args:
            context: 共享执行上下文，含 history 链和用户输入

        Returns:
            AgentResult: 执行结果，data 字段包含本 Agent 的业务产出
        """
        ...

    def _timed(self, coro):
        """包装协程以自动计时和填充 agent_name。

        Args:
            coro: 待执行的协程

        Returns:
            包装后的协程，自动填充 AgentResult.agent_name 和 elapsed_ms
        """
        async def wrapper():
            start = time.perf_counter()
            result = await coro
            elapsed = int((time.perf_counter() - start) * 1000)
            if isinstance(result, AgentResult):
                result.elapsed_ms = elapsed
                result.agent_name = self.name
            return result
        return wrapper()
