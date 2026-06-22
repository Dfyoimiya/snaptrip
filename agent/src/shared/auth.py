"""Auth context — ContextVar for JWT token passthrough.

Shared across agent systems: each tool call that hits the marketplace backend
needs the end-user's JWT for authentication. The token is set by the backend
API handler (or graph node) before invoking agent logic, and read by tool
implementations / HTTP clients.

Thread-safe in async code — each asyncio task gets its own ContextVar copy.
"""

from __future__ import annotations

from contextvars import ContextVar

_auth_token: ContextVar[str] = ContextVar("auth_token", default="")


def set_auth_token(token: str) -> None:
    """Store the JWT token for the current async context."""
    _auth_token.set(token)


def get_auth_token() -> str:
    """Retrieve the JWT token for the current async context."""
    return _auth_token.get()


def auth_header() -> dict[str, str]:
    """Return Authorization header dict, or empty dict if no token is set."""
    token = _auth_token.get()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
