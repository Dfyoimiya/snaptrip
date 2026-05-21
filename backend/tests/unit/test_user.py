"""用户服务单元测试 —— 纯函数/模型测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from datetime import UTC

from marketplace.app.schemas.user import PlanListOut, PlanSlotOut, UserProfileOut


class TestUserSchemas:
    def test_user_profile_out(self):
        p = UserProfileOut(nickname="test", preferences={"food": "spicy"}, travel_style="adventure")
        assert p.nickname == "test"
        assert p.preferences == {"food": "spicy"}
        assert p.travel_style == "adventure"
        assert p.avatar_url is None
        assert p.preference_embedding is None

    def test_plan_list_out(self):
        from datetime import datetime
        now = datetime.now(UTC)
        p = PlanListOut(id=str(uuid.uuid4()), title="Test", status="draft", group_type="solo", created_at=now)
        assert p.status == "draft"
        assert p.group_type == "solo"
        assert p.title == "Test"

    def test_plan_slot_out(self):
        from datetime import datetime
        now = datetime.now(UTC)
        s = PlanSlotOut(id=str(uuid.uuid4()), poi_id="bj-001", time_start=now, time_end=now, slot_status="tentative", buffer_minutes=15)
        assert s.poi_id == "bj-001"
        assert s.slot_status == "tentative"
        assert s.buffer_minutes == 15
