"""Shopping Session Service — Redis-backed session persistence for shopping guide.

Provides session CRUD, message history, LLM-generated summaries, and
cross-session memory retrieval. Mirrors the CS session pattern in MemoryService
but with `shopping_session:` key prefix for complete isolation.

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import json
import logging
import time

from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SESSION_TTL = 1800  # 30 min active session
SUMMARY_TTL = 86400 * 30  # 30 day summary retention
PREFERENCES_TTL = 86400 * 60  # 60 day preference retention
MAX_HISTORY_SESSIONS = 50  # per user
MAX_MESSAGES_PER_SESSION = 100
MAX_PREF_TAGS = 20  # max accumulated style_tags per user
MAX_PREF_CATEGORIES = 10  # max accumulated categories per user
MAX_PREF_BRANDS = 10  # max accumulated brands per user
KEY_PREFIX = "shopping_session"

# ── Summary prompt (lightweight — called after each chat turn) ────────────────

_SUMMARY_PROMPT = """You are a session summarizer for SnapTrip shopping guide.

Given the conversation below, produce a ONE-SENTENCE summary capturing:
- What the user was looking for (product categories, features, price range)
- Any preferences they expressed (brands, styles, constraints)
- Whether they found what they wanted

Also extract structured preference signals for building a user shopping profile.

Conversation:
{conversation}

Reply with ONLY this JSON:
{{"summary": "one sentence", "categories": ["cat1"], "brands": ["brand1"],
  "price_range": [min, max], "style_tags": ["简约", "性价比"],
  "purchase_readiness": "browsing|considering|ready_to_buy", "found": true/false}}
"""


class ShoppingSessionService:
    """Redis-backed session manager for shopping guide agent.

    Key schema:
      shopping_session:{session_id}:meta    → JSON (user_id, created_at, updated_at, message_count, status)
      shopping_session:{session_id}:msgs    → LIST of JSON messages
      shopping_session:{session_id}:summary → JSON summary
      shopping_history:{user_id}            → ZSET (session_id → timestamp)
    """

    def __init__(self, memory: MemoryService) -> None:
        self._memory = memory

    # ── Session lifecycle ─────────────────────────────────────────────────────

    async def create_session(self, user_id: str) -> str:
        """Create a new session. Returns session_id."""
        import uuid

        session_id = str(uuid.uuid4())[:12]
        now = time.time()
        meta = {
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "status": "active",
        }
        # Store metadata
        await self._memory.client.set(
            f"{KEY_PREFIX}:{session_id}:meta",
            json.dumps(meta, ensure_ascii=False),
            ex=SESSION_TTL,
        )
        # Add to user's history index
        history_key = f"shopping_history:{user_id}"
        async with self._memory.client.pipeline() as pipe:
            pipe.zadd(history_key, {session_id: now})
            pipe.zremrangebyrank(history_key, 0, -(MAX_HISTORY_SESSIONS + 1))
            pipe.expire(history_key, SUMMARY_TTL)
            await pipe.execute()

        logger.debug("Created shopping session %s for user %s", session_id, user_id)
        return session_id

    async def touch_session(self, session_id: str) -> None:
        """Refresh session TTL and update timestamp."""
        key = f"{KEY_PREFIX}:{session_id}:meta"
        raw = await self._memory.client.get(key)
        if raw:
            meta = json.loads(raw)
            meta["updated_at"] = time.time()
            await self._memory.client.set(key, json.dumps(meta, ensure_ascii=False), ex=SESSION_TTL)

    async def get_session(self, session_id: str) -> dict | None:
        """Get session metadata."""
        key = f"{KEY_PREFIX}:{session_id}:meta"
        raw = await self._memory.client.get(key)
        return json.loads(raw) if raw else None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages. Summary is preserved."""
        keys = [
            f"{KEY_PREFIX}:{session_id}:meta",
            f"{KEY_PREFIX}:{session_id}:msgs",
        ]
        await self._memory.client.delete(*keys)
        logger.debug("Deleted shopping session %s", session_id)
        return True

    async def list_user_sessions(self, user_id: str) -> list[dict]:
        """List recent sessions for a user (newest first)."""
        history_key = f"shopping_history:{user_id}"
        session_ids = await self._memory.client.zrevrange(history_key, 0, -1)
        sessions: list[dict] = []
        for sid in session_ids:
            meta = await self.get_session(sid)
            if meta:
                meta["id"] = sid
                sessions.append(meta)
        return sessions

    # ── Messages ───────────────────────────────────────────────────────────────

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session's conversation history."""
        key = f"{KEY_PREFIX}:{session_id}:msgs"
        entry = json.dumps(
            {
                "role": role,
                "content": content,
                "ts": time.time(),
            },
            ensure_ascii=False,
        )
        async with self._memory.client.pipeline() as pipe:
            pipe.rpush(key, entry)
            pipe.ltrim(key, -MAX_MESSAGES_PER_SESSION, -1)
            pipe.expire(key, SESSION_TTL)
            await pipe.execute()

        # Update message count in meta
        meta_key = f"{KEY_PREFIX}:{session_id}:meta"
        raw = await self._memory.client.get(meta_key)
        if raw:
            meta = json.loads(raw)
            meta["message_count"] = meta.get("message_count", 0) + 1
            meta["updated_at"] = time.time()
            await self._memory.client.set(meta_key, json.dumps(meta, ensure_ascii=False), ex=SESSION_TTL)

    async def get_messages(self, session_id: str) -> list[dict]:
        """Get all messages for a session."""
        key = f"{KEY_PREFIX}:{session_id}:msgs"
        raw = await self._memory.client.lrange(key, 0, -1)
        return [json.loads(item) for item in raw]

    # ── Summaries ──────────────────────────────────────────────────────────────

    async def save_summary(self, session_id: str, summary: dict) -> None:
        """Save a session summary (persists beyond session TTL for cross-session memory).

        summary dict should contain: user_id, summary_text, categories, price_range, found
        """
        key = f"{KEY_PREFIX}:{session_id}:summary"
        summary["saved_at"] = time.time()
        summary["session_id"] = session_id
        await self._memory.client.set(key, json.dumps(summary, ensure_ascii=False), ex=SUMMARY_TTL)
        logger.debug("Saved summary for session %s", session_id)

    async def get_summary(self, session_id: str) -> dict | None:
        """Get a specific session summary."""
        key = f"{KEY_PREFIX}:{session_id}:summary"
        raw = await self._memory.client.get(key)
        return json.loads(raw) if raw else None

    async def get_user_summaries(self, user_id: str, limit: int = 3) -> list[dict]:
        """Get the user's most recent session summaries for cross-session memory."""
        history_key = f"shopping_history:{user_id}"
        session_ids = await self._memory.client.zrevrange(history_key, 0, limit * 2 - 1)
        summaries: list[dict] = []
        for sid in session_ids:
            summary = await self.get_summary(sid)
            if summary and summary.get("summary_text"):
                summaries.append(summary)
                if len(summaries) >= limit:
                    break
        return summaries

    # ── Summary generation ─────────────────────────────────────────────────────

    @staticmethod
    def build_summary_prompt(messages: list[dict]) -> str:
        """Build a compact prompt for LLM summary generation."""
        # Keep last 6 messages (3 turns) for summary context
        recent = messages[-6:]
        conversation = "\n".join(f"{m['role']}: {str(m['content'])[:300]}" for m in recent)
        return _SUMMARY_PROMPT.format(conversation=conversation)

    async def generate_and_save_summary(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
    ) -> dict | None:
        """Generate an LLM summary and save it. Returns the summary or None on failure."""
        if len(messages) < 2:
            return None

        try:
            from shopping_guide.adapters import get_llm_adapter

            adapter = get_llm_adapter()

            if not adapter:
                logger.debug("No LLM adapter available for summary generation")
                return None

            prompt = self.build_summary_prompt(messages)
            response = await adapter.chat_json(
                prompt=prompt,
                temperature=0.2,
                max_tokens=256,
                timeout_s=5.0,
            )
            if response and response.get("summary"):
                summary = {
                    "user_id": user_id,
                    "summary_text": response.get("summary", ""),
                    "categories": response.get("categories", []),
                    "brands": response.get("brands", []),
                    "price_range": response.get("price_range", []),
                    "style_tags": response.get("style_tags", []),
                    "purchase_readiness": response.get("purchase_readiness", ""),
                    "found": response.get("found", False),
                }
                await self.save_summary(session_id, summary)

                # ── Merge into user-level preference profile ──
                await self.merge_and_save_preferences(user_id, summary)

                return summary
        except Exception:
            logger.warning("Failed to generate summary for session %s", session_id, exc_info=True)
        return None

    # ── User preference profile ────────────────────────────────────────────────

    async def get_user_preferences(self, user_id: str) -> dict:
        """Get the user's accumulated shopping preference profile."""
        key = f"shopping_preferences:{user_id}"
        raw = await self._memory.client.get(key)
        if raw:
            return json.loads(raw)
        return {
            "categories": [],
            "brands": [],
            "style_tags": [],
            "price_range": [0, 0],
            "purchase_readiness": "",
            "total_sessions": 0,
            "updated_at": 0,
        }

    async def merge_and_save_preferences(self, user_id: str, session_summary: dict) -> None:
        """Merge per-session preferences into the user-level profile.

        New preferences are prepended (most recent first) with dedup.
        Limits are enforced on accumulated tags/categories/brands.
        """
        prefs = await self.get_user_preferences(user_id)

        # Merge categories (recent first)
        new_cats = session_summary.get("categories", [])
        existing_cats = prefs.get("categories", [])
        merged_cats = list(dict.fromkeys(new_cats + existing_cats))[:MAX_PREF_CATEGORIES]

        # Merge brands (recent first)
        new_brands = session_summary.get("brands", [])
        existing_brands = prefs.get("brands", [])
        merged_brands = list(dict.fromkeys(new_brands + existing_brands))[:MAX_PREF_BRANDS]

        # Merge style tags (recent first)
        new_tags = session_summary.get("style_tags", [])
        existing_tags = prefs.get("style_tags", [])
        merged_tags = list(dict.fromkeys(new_tags + existing_tags))[:MAX_PREF_TAGS]

        # Price range: expand to encompass both
        new_price = session_summary.get("price_range", [])
        old_min, old_max = prefs.get("price_range", [0, 0])
        if new_price and len(new_price) == 2 and new_price[0] and new_price[1]:
            new_min = min(new_price[0], old_min) if old_min else new_price[0]
            new_max = max(new_price[1], old_max)
        else:
            new_min, new_max = old_min, old_max

        # Purchase readiness: take most recent non-empty
        new_readiness = session_summary.get("purchase_readiness", "")
        old_readiness = prefs.get("purchase_readiness", "")
        readiness = new_readiness or old_readiness

        updated = {
            "categories": merged_cats,
            "brands": merged_brands,
            "style_tags": merged_tags,
            "price_range": [new_min, new_max],
            "purchase_readiness": readiness,
            "total_sessions": prefs.get("total_sessions", 0) + 1,
            "updated_at": time.time(),
        }

        key = f"shopping_preferences:{user_id}"
        await self._memory.client.set(key, json.dumps(updated, ensure_ascii=False), ex=PREFERENCES_TTL)
        logger.debug("Merged shopping preferences for user %s", user_id)

    async def build_preference_context(self, user_id: str) -> str:
        """Build a concise preference summary string for injection into the system context.

        Returns empty string if the user has no meaningful preference data yet.
        """
        prefs = await self.get_user_preferences(user_id)
        if prefs.get("total_sessions", 0) == 0:
            return ""

        parts: list[str] = []
        cats = prefs.get("categories", [])
        if cats:
            parts.append(f"偏好品类: {', '.join(cats[:5])}")

        brands = prefs.get("brands", [])
        if brands:
            parts.append(f"关注品牌: {', '.join(brands[:5])}")

        tags = prefs.get("style_tags", [])
        if tags:
            parts.append(f"风格偏好: {', '.join(tags[:5])}")

        price = prefs.get("price_range", [0, 0])
        if price[1] > 0:
            parts.append(f"预算区间: ¥{price[0]:.0f}-¥{price[1]:.0f}")

        readiness = prefs.get("purchase_readiness", "")
        readiness_map = {
            "browsing": "浏览中",
            "considering": "考虑购买",
            "ready_to_buy": "准备购买",
        }
        if readiness and readiness in readiness_map:
            parts.append(f"购买意向: {readiness_map[readiness]}")

        if not parts:
            return ""

        lines = [f"[User shopping profile (accumulated from {prefs.get('total_sessions', 0)} sessions):]"]
        lines.extend(f"  {p}" for p in parts)
        return "\n".join(lines)

    # ── Cross-session context ──────────────────────────────────────────────────

    async def build_cross_session_context(self, user_id: str) -> str:
        """Build a context string from previous session summaries and user preferences.

        Injected into the first message of a new session so the shopping guide
        remembers the user's past interests and preferences.
        """
        sections: list[str] = []

        # User-level preference profile (accumulated across all sessions)
        pref_context = await self.build_preference_context(user_id)
        if pref_context:
            sections.append(pref_context)

        # Recent session summaries
        summaries = await self.get_user_summaries(user_id, limit=3)
        if summaries:
            lines = ["[Previous shopping context from past sessions:]"]
            for i, s in enumerate(summaries, 1):
                text = s.get("summary_text", "")
                cats = s.get("categories", [])
                price = s.get("price_range", [])
                parts = [text]
                if cats:
                    parts.append(f"Categories: {', '.join(cats[:3])}")
                if price and len(price) == 2:
                    parts.append(f"Price: ¥{price[0]}-¥{price[1]}")
                lines.append(f"  Session {i}: {' | '.join(parts)}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else ""
