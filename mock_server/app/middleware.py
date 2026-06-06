"""Mock Server — 请求鉴权辅助."""

from __future__ import annotations

import time

from fastapi import Request

from app import state


def get_user_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "")
    session = state._sessions.get(token)
    if not session:
        return None
    if session.get("expires_at", 0) < time.time():
        del state._sessions[token]
        return None
    return session.get("user_id")


def get_admin_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "")
    session = state._admin_sessions.get(token)
    if not session:
        return None
    if session.get("expires_at", 0) < time.time():
        del state._admin_sessions[token]
        return None
    return session.get("admin_id")
