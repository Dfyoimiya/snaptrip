"""适配器层入口 —— 暴露核心接口。"""

from app.adapters.base import BaseAmapAdapter
from app.adapters.registry import AdapterRegistry, AdapterRouter

__all__ = ["BaseAmapAdapter", "AdapterRegistry", "AdapterRouter"]
