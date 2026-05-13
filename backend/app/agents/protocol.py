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
    """Agent 执行上下文"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = "default"
    user_input: str = ""
    lat: float = 39.9219
    lng: float = 116.4435
    state: str = "idle"
    history: list[AgentResult] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Agent 执行结果"""
    agent_name: str = ""
    status: str = "success"
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: int = 0


class BaseAgent(ABC):
    """所有 Agent 的抽象基类"""
    name: str = "base"

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        ...

    def _timed(self, coro):
        async def wrapper():
            start = time.perf_counter()
            result = await coro
            elapsed = int((time.perf_counter() - start) * 1000)
            if isinstance(result, AgentResult):
                result.elapsed_ms = elapsed
                result.agent_name = self.name
            return result
        return wrapper()
