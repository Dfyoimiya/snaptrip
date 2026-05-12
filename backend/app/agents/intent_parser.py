"""Intent Parser — LLM 意图解析 + 关键词降级"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.core.constants import INTENT_TIMEOUT_S
from app.schemas.plan import IntentSchema, TimeRange

CITY_KEYWORDS: dict[str, list[str]] = {
    "北京": ["北京", "朝阳", "海淀", "东城", "故宫", "长城", "三里屯", "798", "簋街"],
    "上海": ["上海", "浦东", "外滩", "新天地", "迪士尼", "武康路", "陆家嘴"],
    "重庆": ["重庆", "洪崖洞", "解放碑", "磁器口", "南山", "江北"],
}

TYPE_KEYWORDS: dict[str, list[str]] = {
    "restaurant": ["吃", "饭", "餐厅", "火锅", "烤鸭", "川菜", "美食", "聚餐"],
    "cafe": ["咖啡", "下午茶", "猫咖", "喝茶", "甜点"],
    "attraction": ["逛", "景点", "博物馆", "公园", "打卡", "拍照", "夜景"],
    "activity": ["玩", "运动", "骑行", "乐园", "手工", "陶艺", "看展"],
}

MOOD_KEYWORDS: dict[str, list[str]] = {
    "安静": ["安静", "清净", "放松"],
    "热闹": ["热闹", "嗨", "人气"],
    "浪漫": ["浪漫", "约会", "情侣"],
    "文艺": ["文艺", "小众", "艺术"],
    "亲子": ["带娃", "亲子", "小孩"],
    "治愈": ["治愈", "温暖", "舒服"],
    "辣": ["辣", "麻辣", "重口味"],
    "拍照": ["拍照", "出片", "好看"],
}


class IntentParser(BaseAgent):
    name = "intent_parser"

    async def execute(self, context: AgentContext) -> AgentResult:
        try:
            return await asyncio.wait_for(
                self._parse_via_llm(context), timeout=INTENT_TIMEOUT_S
            )
        except (TimeoutError, Exception):
            return await self._parse_via_keywords(context)

    async def _parse_via_llm(self, context: AgentContext) -> AgentResult:
        try:
            from jinja2 import Template
            with open("app/agents/prompts/intent.j2") as f:
                tpl = Template(f.read())

            prompt = tpl.render(
                user_input=context.user_input,
                current_time=datetime.now().isoformat(),
            )

            import httpx
            async with httpx.AsyncClient(timeout=INTENT_TIMEOUT_S) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": "Bearer placeholder",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek/deepseek-v3",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 512,
                    },
                )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            return await self._parse_via_keywords(context)

        intent = IntentSchema(
            time_window=TimeRange(
                start=parsed.get("time_window", {}).get("start", datetime.now().isoformat()),
                end=parsed.get("time_window", {}).get("end", (datetime.now() + timedelta(hours=4)).isoformat()),
            ) if parsed.get("time_window") else None,
            guest_count=parsed.get("guest_count", 2),
            budget=parsed.get("budget"),
            scene_type=parsed.get("scene_type", "solo"),
            type_prefs=parsed.get("type_prefs", []),
            mood_prefs=parsed.get("mood_prefs", []),
            implicit_constraints=parsed.get("implicit_constraints", []),
            city=parsed.get("city"),
            confidence=parsed.get("confidence", 0.8),
        )
        return AgentResult(data={"intent": intent.model_dump()})

    async def _parse_via_keywords(self, context: AgentContext) -> AgentResult:
        text = context.user_input
        now = datetime.now()

        city = None
        for c, kws in CITY_KEYWORDS.items():
            if any(kw in text for kw in kws):
                city = c
                break

        type_prefs = [t for t, kws in TYPE_KEYWORDS.items() if any(kw in text for kw in kws)]

        mood_prefs = [m for m, kws in MOOD_KEYWORDS.items() if any(kw in text for kw in kws)]

        budget = None
        m = re.search(r"预算(\d+)", text) or re.search(r"人均(\d+)", text)
        if m:
            budget = int(m.group(1)) * (2 if "人均" in m.group(0) else 1)

        count = 2
        m = re.search(r"(\d+)个?人", text)
        if m:
            count = int(m.group(1))

        scene_map = {
            "带娃": "family", "亲子": "family", "小孩": "family",
            "朋友": "friends", "和": "friends",
            "约会": "date", "情侣": "date", "浪漫": "date",
        }
        scene = "solo"
        for kw, s in scene_map.items():
            if kw in text:
                scene = s
                break

        intent = IntentSchema(
            time_window=TimeRange(start=now, end=now + timedelta(hours=4)),
            guest_count=count, budget=budget, scene_type=scene,
            type_prefs=type_prefs, mood_prefs=mood_prefs, city=city,
            confidence=0.4,
        )
        return AgentResult(data={"intent": intent.model_dump()})
