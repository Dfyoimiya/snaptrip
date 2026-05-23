"""Provider 注册表 —— ProviderRegistry + ModelRegistry。

负责：
- 从 models.toml 加载模型配置
- 按 alias 查找模型及对应 Provider
- 管理 Provider 实例生命周期

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from snaptrip_shared.core.exceptions import LLMError

from agent.providers.base import BaseLLMProvider
from agent.schemas.llm import ModelConfig, ModelPricing


class ModelRegistry:
    """模型注册表 —— 从 TOML 加载模型定义"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._models: dict[str, ModelConfig] = {}
        if config_path:
            self._load(config_path)

    def _load(self, config_path: str | Path) -> None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"模型配置文件不存在: {path}")
        data = tomllib.loads(path.read_text())
        for alias, cfg in data.get("models", {}).items():
            try:
                self._models[alias] = ModelConfig(
                    alias=alias,
                    provider=cfg["provider"],
                    api_model=cfg["api_model"],
                    prompt_per_1k=cfg.get("prompt_per_1k", 0.0),
                    completion_per_1k=cfg.get("completion_per_1k", 0.0),
                    max_tokens=cfg.get("max_tokens", 4096),
                    supports_streaming=cfg.get("supports_streaming", True),
                    supports_vision=cfg.get("supports_vision", False),
                )
            except KeyError as e:
                raise LLMError(
                    f"模型 [{alias}] 配置缺少必填字段: {e}",
                    details={"model_alias": alias},
                ) from e

    def register(self, model: ModelConfig) -> None:
        self._models[model.alias] = model

    def get(self, alias: str) -> ModelConfig | None:
        return self._models.get(alias)

    def get_pricing(self, alias: str) -> ModelPricing | None:
        model = self._models.get(alias)
        if model is None:
            return None
        return ModelPricing(
            prompt_per_1k=model.prompt_per_1k,
            completion_per_1k=model.completion_per_1k,
        )

    def list_models(self, provider: str | None = None) -> list[ModelConfig]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models


class ProviderRegistry:
    """Provider 注册表 —— 按名称管理 Provider 实例"""

    def __init__(self, model_registry: ModelRegistry | None = None) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}
        self._model_registry = model_registry or ModelRegistry()

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    def register(self, name: str, provider: BaseLLMProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> BaseLLMProvider | None:
        return self._providers.get(name)

    def resolve(self, model_alias: str) -> tuple[BaseLLMProvider, ModelConfig]:
        """根据模型 alias 解析 Provider + ModelConfig。

        Raises:
            KeyError: 模型或 Provider 未找到（由调用方转换为 LLMError）
        """
        model_cfg = self._model_registry.get(model_alias)
        if model_cfg is None:
            raise KeyError(f"未找到模型配置: {model_alias}")
        provider = self._providers.get(model_cfg.provider)
        if provider is None:
            raise KeyError(f"未找到 Provider: {model_cfg.provider}")
        return provider, model_cfg
