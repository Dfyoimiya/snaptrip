"""Shared infrastructure for agent systems in agent/src/.

Each agent system under agent/src/ shares common tool infrastructure:
  - auth.py   — JWT token passthrough via ContextVar
  - http_client.py — Shared httpx client for calling marketplace backend APIs

Usage:
    from shared.auth import set_auth_token, auth_header
    from shared.http_client import MarketplaceClient

Author: SnapTrip Team
Date: 2026-06-22
"""

from shared.auth import auth_header, get_auth_token, set_auth_token
from shared.http_client import MarketplaceClient

__all__ = [
    "MarketplaceClient",
    "auth_header",
    "get_auth_token",
    "set_auth_token",
]
