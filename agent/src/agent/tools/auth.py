"""Auth context — ContextVar for JWT token passthrough.

The token is set by tool_node from PlanState.working_memory, and read by
tool implementations when making HTTP calls to the marketplace backend.

This is a lightweight ContextVar-based approach that avoids threading issues
in async code — each asyncio task gets its own copy.
"""

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
