"""Intent Parser —— LLM 意图解析 + 关键词降级。

将用户自然语言输入转换为结构化的 IntentSchema。

执行策略:
  1. 首选 LLM 调用（Jinja2 模板渲染 → DeepSeek API）
  2. 超时 2s 或 LLM 不可用时，降级为关键词匹配
  3. 关键词覆盖: 城市/类型/心情/预算/人数/场景

输出:
  IntentSchema: {time_window, guest_count, budget, scene_type,
                  type_prefs, mood_prefs, implicit_constraints, city, confidence}

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta

from snaptrip_shared.core.constants import INTENT_TIMEOUT_S
from snaptrip_shared.core.logging import get_logger
from snaptrip_shared.schemas.plan import IntentSchema, TimeRange

from agent_worker.app.agent.ports.llm import LLMPort
from agent_worker.app.agent.ports.prompt import PromptPort
from agent_worker.app.agent.protocol import AgentContext, AgentResult, BaseAgent

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

logger = get_logger(__name__)


class IntentParser(BaseAgent):
    name = "intent_parser"

    def __init__(
        self,
        llm: LLMPort | None = None,
        prompt_renderer: PromptPort | None = None,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._prompt_renderer = prompt_renderer

    async def execute(self, context: AgentContext) -> AgentResult:
        """优先 LLM 解析，超时降级关键词匹配。

        Args:
            context: 含 user_input 的执行上下文

        Returns:
            AgentResult.data["intent"] = IntentSchema
        """
        logger.info("intent_parser_started", user_id=context.user_id, plan_id=context.plan_id)
        try:
            result = await asyncio.wait_for(self._parse_via_llm(context), timeout=INTENT_TIMEOUT_S)
            logger.info("intent_parser_completed", source="llm", plan_id=context.plan_id)
            return result
        except (TimeoutError, Exception):
            logger.info("intent_parser_fallback", source="keyword", plan_id=context.plan_id)
            return await self._parse_via_keywords(context)

    async def _parse_via_llm(self, context: AgentContext) -> AgentResult:
        """Jinja2 模板渲染 → LLM API。

        解析 LLM 返回的 JSON 为 IntentSchema。
        若 LLM 不可用，降级关键词匹配。

        Args:
            context: 执行上下文

        Returns:
            AgentResult
        """
        try:
            prompt = await self._get_prompt_renderer().render(
                "intent.j2",
                {
                    "user_input": context.user_input,
                    "current_time": datetime.now().isoformat(),
                },
            )
            from snaptrip_shared.core.config import settings

            parsed = await self._get_llm().chat_json(
                prompt=prompt,
                model_alias=settings.LLM_DEFAULT_MODEL,
                timeout_s=INTENT_TIMEOUT_S,
                temperature=0.3,
                max_tokens=512,
            )
        except Exception:
            logger.warning("intent_parser_llm_failed", plan_id=context.plan_id, exc_info=True)
            return await self._parse_via_keywords(context)

        intent = IntentSchema(
            time_window=TimeRange(
                start=parsed.get("time_window", {}).get("start", datetime.now().isoformat()),
                end=parsed.get("time_window", {}).get("end", (datetime.now() + timedelta(hours=4)).isoformat()),
            )
            if parsed.get("time_window")
            else None,
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

    def _get_llm(self) -> LLMPort:
        if self._llm is None:
            from agent_worker.app.agent.adapters.llm import LLMAdapter

            self._llm = LLMAdapter()
        return self._llm

    def _get_prompt_renderer(self) -> PromptPort:
        if self._prompt_renderer is None:
            from agent_worker.app.agent.adapters.prompt import JinjaPromptAdapter

            self._prompt_renderer = JinjaPromptAdapter()
        return self._prompt_renderer

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
            "带娃": "family",
            "亲子": "family",
            "小孩": "family",
            "朋友": "friends",
            "和": "friends",
            "约会": "date",
            "情侣": "date",
            "浪漫": "date",
        }
        scene = "solo"
        for kw, s in scene_map.items():
            if kw in text:
                scene = s
                break

        intent = IntentSchema(
            time_window=TimeRange(start=now, end=now + timedelta(hours=4)),
            guest_count=count,
            budget=budget,
            scene_type=scene,
            type_prefs=type_prefs,
            mood_prefs=mood_prefs,
            city=city,
            confidence=0.4,
        )
        return AgentResult(data={"intent": intent.model_dump()})
