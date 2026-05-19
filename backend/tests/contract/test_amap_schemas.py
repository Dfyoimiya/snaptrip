"""合约测试 —— 高德 API Schema 兼容性验证。

原理:
  预先把高德 API 真实响应存为 JSON 快照，
  定期跑 Pydantic 解析验证。一旦高德变更字段，测试立即发现。

运行方式:
  pytest tests/contract/ -v

Author: SnapTrip Team
Date: 2026-05-19
"""

import json
from pathlib import Path

import pytest

from app.adapters.schemas.poi import AmapPoiResponse
from app.adapters.schemas.route import AmapRouteResponse
from app.adapters.schemas.geocode import AmapGeoResponse

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def load_snapshot(filename: str) -> dict:
    with open(SNAPSHOT_DIR / filename) as f:
        return json.load(f)


class TestPoiSchemaCompat:
    """POI 搜索 Schema 兼容性"""

    def test_parse_snapshot(self):
        data = load_snapshot("amap_poi_search.json")
        response = AmapPoiResponse(**data)

        assert response.status == "1"
        assert response.infocode == "10000"
        assert response.count == "2"
        assert len(response.pois) == 2

    def test_poi_fields_intact(self):
        data = load_snapshot("amap_poi_search.json")
        response = AmapPoiResponse(**data)

        poi = response.pois[0]
        assert poi.id == "B000A7BD6C"
        assert poi.name == "故宫博物院"
        assert poi.location == "116.397,39.908"
        assert poi.cityname == "北京市"
        assert poi.adname == "东城区"
        assert poi.typecode == "110101"

    def test_poi_biz_ext_parsed(self):
        data = load_snapshot("amap_poi_search.json")
        response = AmapPoiResponse(**data)

        poi = response.pois[0]
        assert poi.biz_ext is not None
        assert poi.biz_ext.rating == "4.8"
        assert poi.biz_ext.cost == "60"
        assert poi.biz_ext.open_time == "08:30-17:00"

    def test_poi_without_biz_ext(self):
        data = load_snapshot("amap_poi_search.json")
        response = AmapPoiResponse(**data)

        poi = response.pois[1]
        assert poi.biz_ext is not None
        assert poi.biz_ext.rating == "4.5"
        assert poi.biz_ext.cost is None

    def test_empty_pois(self):
        response = AmapPoiResponse(
            status="1",
            infocode="10000",
            info="OK",
            count="0",
            pois=[],
        )
        assert response.count == "0"
        assert response.pois == []


class TestRouteSchemaCompat:
    """路径规划 Schema 兼容性"""

    def test_parse_snapshot(self):
        data = load_snapshot("amap_route_walking.json")
        response = AmapRouteResponse(**data)

        assert response.status == "1"
        assert response.infocode == "10000"
        assert response.route is not None
        assert len(response.route.paths) == 1

    def test_path_fields_intact(self):
        data = load_snapshot("amap_route_walking.json")
        response = AmapRouteResponse(**data)

        path = response.route.paths[0]
        assert path.distance == "3200"
        assert path.duration == "2100"
        assert path.tolls == "0"
        assert len(path.steps) == 2

    def test_step_fields_intact(self):
        data = load_snapshot("amap_route_walking.json")
        response = AmapRouteResponse(**data)

        step = response.route.paths[0].steps[0]
        assert step.road == "景山前街"
        assert step.distance == "500"
        assert step.duration == "360"
        assert step.instruction == "向北步行500米"


class TestGeocodeSchemaCompat:
    """地理编码 Schema 兼容性"""

    def test_parse_snapshot(self):
        data = load_snapshot("amap_geocode.json")
        response = AmapGeoResponse(**data)

        assert response.status == "1"
        assert response.infocode == "10000"
        assert response.count == "1"
        assert len(response.geocodes) == 1

    def test_geocode_fields_intact(self):
        data = load_snapshot("amap_geocode.json")
        response = AmapGeoResponse(**data)

        geo = response.geocodes[0]
        assert geo.formatted_address == "北京市东城区景山前街4号"
        assert geo.province == "北京市"
        assert geo.city == "北京市"
        assert geo.district == "东城区"
        assert geo.location == "116.397,39.908"
        assert geo.level == "门牌号"


class TestSchemaResilience:
    """Schema 韧性测试 —— 缺失可选字段不抛异常"""

    def test_minimal_poi(self):
        response = AmapPoiResponse(
            status="0",
            infocode="10000",
            info="OK",
            count="0",
            pois=[],
        )
        assert response.pois == []

    def test_minimal_route(self):
        response = AmapRouteResponse(
            status="0",
            infocode="10000",
            info="OK",
        )
        assert response.route.paths == []

    def test_minimal_geocode(self):
        response = AmapGeoResponse(
            status="0",
            infocode="10000",
            info="OK",
        )
        assert response.geocodes == []
