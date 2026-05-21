"""Tool Registry —— 从 tools.toml 加载工具配置。

职责:
  - 加载 tools.toml → ToolProviderConfig
  - 按名称查找工具配置
  - 提供 to_ToolDefinition() 适配现有 TOOL_REGISTRY

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from app.schemas.tool import ToolDefinition
from app.schemas.tool_provider import ToolProviderConfig


class ToolRegistry:
    """工具注册表 —— 从 TOML 加载工具运行时配置。

    单一数据源: providers/tools/tools.toml
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._tools: dict[str, ToolProviderConfig] = {}
        if config_path:
            self._load(config_path)

    # ------------------------------------------------------------------
    # load / register
    # ------------------------------------------------------------------

    def _load(self, config_path: str | Path) -> None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"工具配置文件不存在: {path}")

        data = tomllib.loads(path.read_bytes().decode())
        for name, cfg in data.get("tools", {}).items():
            self._tools[name] = ToolProviderConfig(
                name=name,
                provider=cfg.get("provider", "mock"),
                human_readable_name=cfg.get("human_readable_name", ""),
                llm_description=cfg.get("llm_description", ""),
                is_idempotent=cfg.get("is_idempotent", True),
                physical_impact=cfg.get("physical_impact", False),
                timeout_ms=cfg.get("timeout_ms", 3000),
                max_retries=cfg.get("max_retries", 2),
                retry_delay_ms=cfg.get("retry_delay_ms", 1000),
                idempotency_ttl_sec=cfg.get("idempotency_ttl_sec", 3600),
                circuit_breaker_threshold=cfg.get("circuit_breaker_threshold", 5),
                circuit_recovery_s=cfg.get("circuit_recovery_s", 30),
                compensation=cfg.get("compensation"),
            )

    def register(self, config: ToolProviderConfig) -> None:
        self._tools[config.name] = config

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def get(self, name: str) -> ToolProviderConfig | None:
        return self._tools.get(name)

    def all(self) -> dict[str, ToolProviderConfig]:
        return dict(self._tools)

    def list_physical(self) -> list[ToolProviderConfig]:
        """列出所有物理操作工具。"""
        return [t for t in self._tools.values() if t.physical_impact]

    def list_by_provider(self, provider: str) -> list[ToolProviderConfig]:
        return [t for t in self._tools.values() if t.provider == provider]

    # ------------------------------------------------------------------
    # conversion
    # ------------------------------------------------------------------

    def to_tool_definitions(self, existing_defs: dict[str, ToolDefinition] | None = None) -> dict[str, ToolDefinition]:
        """将 TOML 配置转为 ToolDefinition 字典。

        优先使用 TOML 中的 llm_description/human_readable_name/physical_impact，
        其余字段（layer, dependencies, input_schema, output_schema 等）从现有
        TOOL_REGISTRY 继承。
        """
        result: dict[str, ToolDefinition] = {}
        existing = existing_defs or {}

        for name, cfg in self._tools.items():
            base = existing.get(name)
            if base:
                result[name] = ToolDefinition(
                    name=name,
                    human_readable_name=cfg.human_readable_name or base.human_readable_name,
                    llm_description=cfg.llm_description or base.llm_description,
                    description=base.description,
                    input_schema=base.input_schema,
                    output_schema=base.output_schema,
                    layer=base.layer,
                    dependencies=base.dependencies,
                    is_idempotent=cfg.is_idempotent,
                    default_timeout_ms=cfg.timeout_ms,
                    fallback_policy=base.fallback_policy,
                    physical_impact=cfg.physical_impact,
                )
            else:
                result[name] = ToolDefinition(
                    name=name,
                    human_readable_name=cfg.human_readable_name,
                    llm_description=cfg.llm_description,
                    description=cfg.human_readable_name,
                    is_idempotent=cfg.is_idempotent,
                    default_timeout_ms=cfg.timeout_ms,
                    physical_impact=cfg.physical_impact,
                )
        return result
