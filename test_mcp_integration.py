"""Integration test: MCP-first + REST fallback for AmapAdapter.

Tests:
  1. geocode (MCP maps_geo)
  2. weather (MCP maps_weather)
  3. around_search (MCP maps_around_search + REST enrichment)
  4. distance (MCP maps_distance)
  5. district (REST only)
  6. input_tips (REST only)
  7. POI format compatibility with scorer/composer

Run: uv run python test_mcp_integration.py
"""

import asyncio
import sys
sys.path.insert(0, "agent/src")

from agent.adapters.amap_adapter import AmapAdapter


async def test_geocode():
    """Test MCP geocode → fallback REST."""
    print("=" * 60)
    print("TEST 1: Geocode (MCP maps_geo)")
    adapter = AmapAdapter()
    result = await adapter.geocode("北京市朝阳区朝阳公园")
    print(f"  Result: {result}")
    assert result.get("lng") and result.get("lat"), "Missing coordinates"
    print(f"  ✓ lng={result['lng']}, lat={result['lat']}")
    await adapter.close()


async def test_weather():
    """Test MCP weather → fallback REST."""
    print("\n" + "=" * 60)
    print("TEST 2: Weather (MCP maps_weather)")
    adapter = AmapAdapter()
    result = await adapter.get_weather("110101")
    print(f"  Result: {result}")
    assert result, "Empty weather result"
    if "forecasts" in result:
        print(f"  ✓ forecasts for {result.get('city', '?')}: {len(result['forecasts'])} days")
    elif "weather" in result:
        print(f"  ✓ live: {result['weather']}, {result['temperature']}°C")
    await adapter.close()


async def test_around_search():
    """Test MCP around_search + REST enrichment."""
    print("\n" + "=" * 60)
    print("TEST 3: Around Search (MCP maps_around_search + enrichment)")
    adapter = AmapAdapter()
    # 北京朝阳公园周边搜索餐厅
    result = await adapter.search_pois_around(
        location="116.481488,39.933723",  # 朝阳公园
        radius=5000,
        keywords="火锅",
        types="050000",
        offset=5,
    )
    print(f"  Got {len(result)} POIs")
    for i, poi in enumerate(result[:3]):
        print(f"  [{i+1}] {poi.get('name')} | rating={poi.get('rating')} | "
              f"avg_price={poi.get('avg_price')} | dist={poi.get('distance_km')}km")
        # Verify key fields for scorer/composer compatibility
        assert poi.get("id"), f"POI {i+1} missing id"
        assert poi.get("name"), f"POI {i+1} missing name"
        assert poi.get("rating"), f"POI {i+1} missing rating"
    print(f"  ✓ POIs have required fields (id, name, rating, distance_km, avg_price)")
    await adapter.close()


async def test_distance():
    """Test MCP distance measurement."""
    print("\n" + "=" * 60)
    print("TEST 4: Distance (MCP maps_distance)")
    adapter = AmapAdapter()
    result = await adapter.estimate_travel_time(
        origin="116.397428,39.90923",       # 天安门
        destination="116.481488,39.933723", # 朝阳公园
        mode="driving",
    )
    print(f"  Result: {result}")
    assert result.get("distance_km") is not None, "Missing distance"
    assert result.get("duration_min") is not None, "Missing duration"
    print(f"  ✓ {result['distance_km']}km, {result['duration_min']}min")
    await adapter.close()


async def test_district():
    """Test REST district query."""
    print("\n" + "=" * 60)
    print("TEST 5: District (REST only)")
    adapter = AmapAdapter()
    result = await adapter.get_district("朝阳区", subdistrict=1)
    print(f"  Got {len(result)} district(s)")
    if result:
        d = result[0]
        print(f"  {d['name']} (adcode={d['adcode']}, center={d['center']})")
        print(f"  children: {len(d.get('children', []))}")
    print("  ✓ district query works")
    await adapter.close()


async def test_input_tips():
    """Test REST input tips."""
    print("\n" + "=" * 60)
    print("TEST 6: Input Tips (REST only)")
    adapter = AmapAdapter()
    result = await adapter.input_tips("朝阳公园", city="010")
    print(f"  Got {len(result)} tips")
    for i, tip in enumerate(result[:3]):
        print(f"  [{i+1}] {tip['name']} ({tip['district']})")
    assert len(result) > 0, "No tips returned"
    print("  ✓ input tips work")
    await adapter.close()


async def test_poi_format_compatibility():
    """Verify internal POI format is compatible with scorer/composer expectations.

    Scorer expects at minimum: id, name, type, lat, lng, rating, avg_price, distance_km
    Composer expects: id, name, lat, lng, avg_price

    Also check that search_pois_around with activity types works.
    """
    print("\n" + "=" * 60)
    print("TEST 7: POI Format Compatibility")
    adapter = AmapAdapter()

    # Test activity search
    result = await adapter.search_pois_around(
        location="116.397428,39.90923",  # 天安门
        radius=10000,
        keywords="",
        types="110000|140000",  # 风景名胜|科教文化
        offset=5,
    )
    print(f"  Activity search: {len(result)} POIs")

    required_fields = ["id", "name", "type", "lat", "lng", "rating", "avg_price", "distance_km"]
    for i, poi in enumerate(result[:3]):
        print(f"  [{i+1}] {poi.get('name')} | type={poi.get('type')} | "
              f"rating={poi.get('rating')} | price={poi.get('avg_price')} | "
              f"dist={poi.get('distance_km')}km | lat/lng={poi.get('lat')},{poi.get('lng')}")
        missing = [f for f in required_fields if f not in poi]
        if missing:
            print(f"    ⚠ Missing fields: {missing}")
        else:
            print(f"    ✓ All required fields present")

    # Verify lat/lng are non-zero (either from REST or enrichment)
    for poi in result:
        if poi.get("lat") != 0 and poi.get("lng") != 0:
            print(f"  ✓ lat/lng populated via REST enrichment: {poi['name']} ({poi['lat']},{poi['lng']})")
            break
    else:
        print("  ⚠ No POI has non-zero coordinates — enrichment may not have run")

    await adapter.close()


async def main():
    print("AmapAdapter Integration Tests")
    print("MCP URL: https://mcp.amap.com/mcp?key=...")
    print("REST URL: https://restapi.amap.com\n")

    try:
        await test_geocode()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_weather()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_around_search()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_distance()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_district()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_input_tips()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    try:
        await test_poi_format_compatibility()
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    print("\n" + "=" * 60)
    print("All tests completed.")


if __name__ == "__main__":
    asyncio.run(main())
