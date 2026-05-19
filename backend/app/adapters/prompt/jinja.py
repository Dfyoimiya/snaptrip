"""Jinja prompt adapter."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from app.ports.prompt import PromptPort


class JinjaPromptAdapter(PromptPort):
    """Loads prompts from the existing prompts directory."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path(__file__).resolve().parents[2] / "agents" / "prompts"

    async def render(self, template_name: str, context: dict) -> str:
        template_path = self._base_dir / template_name
        with template_path.open(encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**context)
