"""Intent Parser 关键词解析测试"""

import pytest

from app.agents.intent_parser import IntentParser
from app.agents.protocol import AgentContext


@pytest.mark.asyncio
async def test_parse_city_chongqing():
    parser = IntentParser()
    ctx = AgentContext(user_input="想吃重庆火锅，两个人")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["city"] == "重庆"
    assert "restaurant" in intent["type_prefs"]


@pytest.mark.asyncio
async def test_parse_city_beijing():
    parser = IntentParser()
    ctx = AgentContext(user_input="周末去北京故宫逛逛")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["city"] == "北京"
    assert "attraction" in intent["type_prefs"]


@pytest.mark.asyncio
async def test_parse_scene_family():
    parser = IntentParser()
    ctx = AgentContext(user_input="带娃去迪士尼玩")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["scene_type"] == "family"


@pytest.mark.asyncio
async def test_parse_scene_date():
    parser = IntentParser()
    ctx = AgentContext(user_input="情侣约会去哪里")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["scene_type"] == "date"


@pytest.mark.asyncio
async def test_parse_guest_count():
    parser = IntentParser()
    ctx = AgentContext(user_input="3个人去吃火锅")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["guest_count"] == 3


@pytest.mark.asyncio
async def test_parse_guest_count_default():
    parser = IntentParser()
    ctx = AgentContext(user_input="想去喝咖啡")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["guest_count"] == 2


@pytest.mark.asyncio
async def test_parse_budget_explicit():
    parser = IntentParser()
    ctx = AgentContext(user_input="预算300吃川菜")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["budget"] == 300


@pytest.mark.asyncio
async def test_parse_budget_per_person():
    parser = IntentParser()
    ctx = AgentContext(user_input="人均100吃川菜")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["budget"] == 200


@pytest.mark.asyncio
async def test_parse_mood_quiet():
    parser = IntentParser()
    ctx = AgentContext(user_input="找个安静的地方放松一下")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert "安静" in intent["mood_prefs"]


@pytest.mark.asyncio
async def test_parse_mood_photo():
    parser = IntentParser()
    ctx = AgentContext(user_input="下午去拍照打卡")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert "attraction" in intent["type_prefs"]
    assert "拍照" in intent["mood_prefs"]


@pytest.mark.asyncio
async def test_parse_no_city():
    parser = IntentParser()
    ctx = AgentContext(user_input="想喝咖啡")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["city"] is None
    assert "cafe" in intent["type_prefs"]


@pytest.mark.asyncio
async def test_parse_confidence_low():
    parser = IntentParser()
    ctx = AgentContext(user_input="随便去哪")
    result = await parser._parse_via_keywords(ctx)
    intent = result.data["intent"]
    assert intent["confidence"] < 0.6
