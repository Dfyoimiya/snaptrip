"""Retrieval Engine — haversine 距离 + 城市过滤"""

from agent_worker.app.agent.engines.retrieval_engine import haversine


class TestHaversine:
    def test_same_point_zero(self):
        assert haversine(39.9, 116.4, 39.9, 116.4) == 0.0

    def test_beijing_shanghai(self):
        d = haversine(39.9042, 116.4074, 31.2304, 121.4737)
        assert 1000 < d < 1150

    def test_symmetric(self):
        d1 = haversine(30, 120, 40, 130)
        d2 = haversine(40, 130, 30, 120)
        assert abs(d1 - d2) < 0.01

    def test_short_distance(self):
        d = haversine(39.90, 116.40, 39.91, 116.41)
        assert d < 3.0
