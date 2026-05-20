"""LLM 相关 Pydantic Schema —— 统一 Provider 层的输入输出。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ===== 核心结果 =====


class TokenUsage(BaseModel):
    """Token 用量统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResult(BaseModel):
    """单次 LLM chat 完整结果"""
    content: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str = "stop"
    latency_ms: int = 0
    provider: str = ""


class StreamChunk(BaseModel):
    """流式 chat 增量 delta"""
    content: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    model: str = ""


# ===== 模型配置 =====


class ModelPricing(BaseModel):
    """模型定价（USD / 1K tokens）"""
    prompt_per_1k: float = 0.0
    completion_per_1k: float = 0.0


class ModelConfig(BaseModel):
    """模型配置条目"""
    alias: str                                    # "deepseek-v4-pro"
    provider: str                                 # "deepseek"
    api_model: str                                # "deepseek-chat"
    prompt_per_1k: float = 0.0
    completion_per_1k: float = 0.0
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_vision: bool = False
