"""PoiMapper 单元测试 —— 高德 POI → 内部 POI Schema 转换。

测试覆盖:
  - 正常转换: 标准 AmapPoiItem → 内部 POI
  - 坐标解析: location 各种格式
  - 类型映射: typecode → POIType
  - 边界情况: 空字段 / 错误数据
"""

from marketplace.app.adapters.amap.poi_mapper import PoiMapper, _map_typecode_to_poi_type, _parse_location
from marketplace.app.adapters.amap.schemas.poi import AmapPoiBizExt, AmapPoiItem


class TestLocationParsing:
    def test_normal_location(self):
        lat, lng = _parse_location("116.397,39.908")
        assert lat == 39.908
        assert lng == 116.397

    def test_empty_location(self):
        lat, lng = _parse_location("")
        assert lat == 0.0
        assert lng == 0.0

    def test_invalid_location(self):
        lat, lng = _parse_location("invalid,data")
        assert lat == 0.0
        assert lng == 0.0

    def test_no_comma(self):
        lat, lng = _parse_location("116.397")
        assert lat == 0.0
        assert lng == 0.0

    def test_negative_coordinates(self):
        lat, lng = _parse_location("-74.006,-40.7128")
        assert lat == -40.7128
        assert lng == -74.006


class TestTypecodeMapping:
    def test_restaurant_typecode(self):
        assert _map_typecode_to_poi_type("050100") == "restaurant"

    def test_attraction_typecode(self):
        assert _map_typecode_to_poi_type("110100") == "scenery"

    def test_unknown_typecode_defaults_to_attraction(self):
        assert _map_typecode_to_poi_type("999999") == "attraction"

    def test_empty_typecode(self):
        assert _map_typecode_to_poi_type("") == "attraction"


class TestPoiMapper:
    def test_basic_conversion(self):
        amap_poi = AmapPoiItem(
            id="B000A7BD6C",
            name="测试餐厅",
            typecode="050100",
            location="116.397,39.908",
            cityname="北京",
            address="朝阳区测试路1号",
            biz_ext=AmapPoiBizExt(rating="4.5", cost="80", open_time="10:00-22:00"),
        )

        poi = PoiMapper.to_internal(amap_poi)

        assert poi.id == "B000A7BD6C"
        assert poi.name == "测试餐厅"
        assert poi.city == "北京"
        assert poi.type == "restaurant"
        assert poi.lat == 39.908
        assert poi.lng == 116.397
        assert poi.avg_price == 80
        assert poi.rating == 4.5
        assert poi.business_hours == "10:00-22:00"

    def test_conversion_without_biz_ext(self):
        amap_poi = AmapPoiItem(
            id="B000A7BD6C",
            name="无名景点",
            typecode="110100",
            location="121.4737,31.2304",
            cityname="上海",
        )

        poi = PoiMapper.to_internal(amap_poi)

        assert poi.id == "B000A7BD6C"
        assert poi.city == "上海"
        assert poi.type == "scenery"
        assert poi.avg_price == 0
        assert poi.rating == 0.0
        assert poi.business_hours == "09:00-22:00"

    def test_conversion_with_city_override(self):
        amap_poi = AmapPoiItem(
            id="B000A7BD6C",
            name="某地点",
            typecode="060100",
            location="106.5516,29.563",
            cityname="",
        )

        poi = PoiMapper.to_internal(amap_poi, city_override="重庆")

        assert poi.city == "重庆"

    def test_invalid_cost_and_rating(self):
        amap_poi = AmapPoiItem(
            id="X",
            name="坏数据店铺",
            typecode="050100",
            location="0,0",
            biz_ext=AmapPoiBizExt(rating="不是数字", cost="也不是数字"),
        )

        poi = PoiMapper.to_internal(amap_poi)
        assert poi.avg_price == 0
        assert poi.rating == 0.0

    def test_batch_conversion(self):
        amap_pois = [
            AmapPoiItem(id="p1", name="POI 1", typecode="050100", location="116.40,39.92", cityname="北京"),
            AmapPoiItem(id="p2", name="POI 2", typecode="110100", location="116.41,39.93", cityname="北京"),
        ]

        pois = PoiMapper.to_internal_batch(amap_pois)

        assert len(pois) == 2
        assert pois[0].id == "p1"
        assert pois[0].type == "restaurant"
        assert pois[1].id == "p2"
        assert pois[1].type == "scenery"

    def test_mood_tags_generated(self):
        amap_poi = AmapPoiItem(id="p1", name="某咖啡馆", typecode="050100", location="116.40,39.92", cityname="北京")
        poi = PoiMapper.to_internal(amap_poi)
        assert len(poi.mood_tags) > 0
        assert "聚餐" in poi.mood_tags or "美食" in poi.mood_tags


class TestGeoMapper:
    def test_normal_parse(self):
        from marketplace.app.adapters.amap.geo_mapper import GeoMapper

        lat, lng = GeoMapper.parse_location("116.397,39.908")
        assert lat == 39.908
        assert lng == 116.397

    def test_format_location(self):
        from marketplace.app.adapters.amap.geo_mapper import GeoMapper

        assert GeoMapper.format_location(39.908, 116.397) == "116.397000,39.908000"

    def test_valid_coordinates(self):
        from marketplace.app.adapters.amap.geo_mapper import GeoMapper

        assert GeoMapper.is_valid_coordinate(39.9, 116.4) is True
        assert GeoMapper.is_valid_coordinate(91.0, 0.0) is False
        assert GeoMapper.is_valid_coordinate(0.0, 181.0) is False
        assert GeoMapper.is_valid_coordinate(-90.0, -180.0) is True

    def test_build_origin_dest(self):
        from marketplace.app.adapters.amap.geo_mapper import GeoMapper

        origin, dest = GeoMapper.build_origin_dest(39.908, 116.397, 39.92, 116.40)
        assert origin == "116.397000,39.908000"
        assert dest == "116.400000,39.920000"


class TestRouteMapper:
    def test_normal_conversion(self):
        from marketplace.app.adapters.amap.route_mapper import RouteMapper
        from marketplace.app.adapters.amap.schemas.route import AmapPath, AmapStep

        path = AmapPath(
            distance="1500",
            duration="900",
            tolls="0",
            traffic_lights="3",
            steps=[
                AmapStep(
                    instruction="向北步行100米",
                    road="朝阳路",
                    distance="100",
                    duration="60",
                    polyline="116.397,39.908;116.398,39.909",
                ),
                AmapStep(
                    instruction="左转进入测试路",
                    road="测试路",
                    distance="1400",
                    duration="840",
                    polyline="116.398,39.909;116.40,39.92",
                ),
            ],
        )

        result = RouteMapper.to_internal(path)

        assert result["distance_km"] == 1.5
        assert result["distance_m"] == 1500
        assert result["duration_min"] == 15
        assert result["tolls"] == "0"
        assert result["traffic_lights"] == "3"
        assert result["step_count"] == 2
        assert result["polyline"] == "116.397,39.908;116.398,39.909;116.398,39.909;116.40,39.92"

    def test_empty_path(self):
        from marketplace.app.adapters.amap.route_mapper import RouteMapper
        from marketplace.app.adapters.amap.schemas.route import AmapPath

        path = AmapPath()
        result = RouteMapper.to_internal(path)

        assert result["distance_km"] == 0.0
        assert result["duration_min"] == 1
        assert result["step_count"] == 0

    def test_route_summary_picks_shortest(self):
        from marketplace.app.adapters.amap.route_mapper import RouteMapper
        from marketplace.app.adapters.amap.schemas.route import AmapPath

        paths = [
            AmapPath(distance="2000", duration="1200"),
            AmapPath(distance="1000", duration="600"),
            AmapPath(distance="3000", duration="1800"),
        ]

        summary = RouteMapper.to_route_summary(paths)
        assert summary["distance_m"] == 1000
        assert summary["duration_min"] == 10

    def test_route_summary_empty(self):
        from marketplace.app.adapters.amap.route_mapper import RouteMapper

        summary = RouteMapper.to_route_summary([])
        assert summary["distance_km"] == 0
        assert summary["duration_min"] == 0
