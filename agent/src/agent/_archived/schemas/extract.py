# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""Extract 阶段数据模型 —— 意图 / 需求 / 硬约束 / 软约束。

Pydantic 模型定义 + ExtractResult 聚合校验：
- is_sufficient() — 判定数据是否完备到可进入 plan 阶段
- missing_fields() — 返回仍需澄清的字段列表
- clarification_question() — 按优先级生成下一轮提问

Author: SnapTrip Team
Date: 2026-05-31
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────
# TODO: 加入用户画像学习


class SceneType(StrEnum):
    """场景类型"""
    FAMILY = "family"
    FRIENDS = "friends"
    COUPLE = "couple"
    SOLO = "solo"


class TransportMode(StrEnum):
    """交通方式"""
    WALK = "walk"
    TRANSIT = "transit"
    DRIVE = "drive"


class BudgetPreference(StrEnum):
    """预算偏好"""
    # TODO: 量化定义 
    ECONOMY = "economy"
    MID = "mid"
    LUXURY = "luxury"


class TravelPace(StrEnum):
    """出行节奏"""
    # TODO: 量化定义
    RELAXED = "relaxed"
    BALANCED = "balanced"
    FAST = "fast"


# ── Sub-models ─────────────────────────────────────────────


class UserIntent(BaseModel):
    """用户出行意图 —— 从对话中提取的核心参数。

    字段逐一对应求解器输入，null 表示尚未提取。
    """

    city: str | None = Field(default=None, description="目标城市")
    plan_date: str | None = Field(default=None, description="出行日期 YYYY-MM-DD")
    time_window_start: str | None = Field(default=None, description="开始时间 HH:MM")
    time_window_hours: float | None = Field(
        default=None, description="可用时长（小时）"
    )
    guest_count: int | None = Field(default=None, description="参与人数", ge=1)
    scene: SceneType | None = Field(default=None, description="场景类型")
    raw_utterance: str | None = Field(
        default=None, description="用户原始自然语言输入"
    )


class UserRequirements(BaseModel):
    """用户明确提出的需求——应被满足但非硬约束。

    为空的 list 表示用户未提出此类需求。
    """

    must_visit_pois: list[str] = Field(
        default_factory=list, description="用户指定的必去地点名称"
    )
    must_have_cuisine: list[str] = Field(
        default_factory=list, description="必须包含的菜系"
    )
    must_have_activity_type: list[str] = Field(
        default_factory=list, description="必须包含的活动类型"
    )
    special_requests: list[str] = Field(
        default_factory=list, description="特殊需求（生日蛋糕、鲜花、纪念日等）"
    )
    notes: str | None = Field(default=None, description="其他自由文本备注")


class HardConstraints(BaseModel):
    """硬约束 —— 数学意义上的约束条件，不可协商放松。

    求解器用这些字段做 feasibility check，违反则直接 infeasible。
    """

    budget_max_cny: float | None = Field(
        default=None, description="预算上限（元）", ge=0
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list, description="饮食限制（清真、素食、过敏原等）"
    )
    child_age: int | None = Field(
        default=None, description="儿童年龄（影响亲子友好筛选）", ge=0
    )
    accessibility_needed: bool = Field(default=False, description="无障碍需求")
    time_deadline: str | None = Field(
        default=None, description="必须在此时间前结束 HH:MM"
    )
    must_include_poi_ids: list[str] = Field(
        default_factory=list, description="必须包含的 POI ID 列表"
    )


class SoftConstraints(BaseModel):
    """软约束/偏好 —— 可协商放松。

    求解无解时按以下优先级放松:
    1. preferred_poi_types（放宽类型偏好）
    2. travel_pace（放宽节奏限制）
    3. budget_preference（放宽预算偏好）
    4. max_transit_minutes（放宽转场时间）
    """

    budget_preference: BudgetPreference | None = Field(
        default=None, description="预算偏好"
    )
    travel_pace: TravelPace | None = Field(default=None, description="出行节奏")
    preferred_poi_types: list[str] = Field(
        default_factory=list, description="偏好 POI 类型"
    )
    preferred_cuisines: list[str] = Field(
        default_factory=list, description="偏好菜系"
    )
    preferred_transport: TransportMode | None = Field(
        default=None, description="偏好交通方式"
    )
    max_transit_minutes: float | None = Field(
        default=None, description="单程最大转场时间（分钟）"
    )
    avoid_poi_types: list[str] = Field(
        default_factory=list, description="不想去的类型"
    )


# ── Aggregate ──────────────────────────────────────────────


class ExtractResult(BaseModel):
    """Extract 阶段的完整输出 —— 意图 + 需求 + 硬约束 + 软约束。

    核心校验逻辑:
    - is_sufficient()  → True == 数据完备，可流转至 plan 节点
    - missing_fields() → 缺失字段列表（用于引导 LLM 澄清）
    - clarification_question() → 按优先级生成下一轮提问
    """

    intent: UserIntent = Field(default_factory=UserIntent)
    requirements: UserRequirements = Field(default_factory=UserRequirements)
    hard_constraints: HardConstraints = Field(default_factory=HardConstraints)
    soft_constraints: SoftConstraints = Field(default_factory=SoftConstraints)
    confidence: float = Field(
        default=0.0, description="提取置信度 0-1", ge=0.0, le=1.0
    )

    # ── 必要字段 —— 缺一不可 ──
    REQUIRED_INTENT_FIELDS: tuple[str, ...] = (
        "city",
        "plan_date",
        "time_window_start",
        "time_window_hours",
        "guest_count",
    )
    REQUIRED_HARD_FIELDS: tuple[str, ...] = ("budget_max_cny",)

    def is_sufficient(self) -> bool:
        """判定 extract 阶段是否完成。

        规则:
        1. intent 必要字段必须全部非空
        2. hard_constraints.budget_max_cny 必须非空
        3. requirements / soft_constraints 全可选——空 = 无偏好
        """
        for field in self.REQUIRED_INTENT_FIELDS:
            if getattr(self.intent, field, None) is None:
                return False
        for field in self.REQUIRED_HARD_FIELDS:
            if getattr(self.hard_constraints, field, None) is None:
                return False
        return True

    def missing_fields(self) -> list[str]:
        """返回当前缺失的必要字段列表（dotted path 形式）。"""
        missing: list[str] = []
        for field in self.REQUIRED_INTENT_FIELDS:
            if getattr(self.intent, field, None) is None:
                missing.append(f"intent.{field}")
        for field in self.REQUIRED_HARD_FIELDS:
            if getattr(self.hard_constraints, field, None) is None:
                missing.append(f"hard_constraints.{field}")
        return missing

    def clarification_question(self) -> str | None:
        """根据缺失字段生成下一轮澄清问题。

        按优先级返回最关键缺失字段对应的问题。
        全部完备时返回 None。
        """
        missing = self.missing_fields()
        if not missing:
            return None

        _questions: dict[str, str] = {
            "intent.city": "请问您想去哪个城市？",
            "intent.plan_date": "请问您计划哪天出行？",
            "intent.time_window_start": "请问您计划几点开始？",
            "intent.time_window_hours": "请问您有多少时间可用？",
            "intent.guest_count": "请问一共几个人？",
            "hard_constraints.budget_max_cny": "请问您的预算上限是多少？",
        }
        for m in missing:
            if m in _questions:
                return _questions[m]
        return f"还需要了解: {', '.join(missing)}"

    def apply_update(self, update: UpdateExtractResultInput) -> list[str]:
        """增量合并更新字段。只更新非 None 值，返回被更新的字段名列表。

        不会覆盖用户已确认的非 None 值——新值仅在新值与旧值不同时写入。
        这是"增量合并"语义：LLM 每次只传本次对话新提取的字段。
        """
        updated: list[str] = []

        if update.intent is not None:
            intent_updates = update.intent.model_dump(exclude_none=True)
            for k, v in intent_updates.items():
                current = getattr(self.intent, k, None)
                if current is None or current != v:
                    setattr(self.intent, k, v)
                    updated.append(f"intent.{k}")

        if update.requirements is not None:
            req_updates = update.requirements.model_dump(exclude_none=True)
            for k, v in req_updates.items():
                current = getattr(self.requirements, k, None)
                if isinstance(v, list) and isinstance(current, list):
                    # lists: merge unique
                    merged = list(dict.fromkeys(current + v))
                    if merged != current:
                        setattr(self.requirements, k, merged)
                        updated.append(f"requirements.{k}")
                elif current is None or current != v:
                    setattr(self.requirements, k, v)
                    updated.append(f"requirements.{k}")

        if update.hard_constraints is not None:
            hc_updates = update.hard_constraints.model_dump(exclude_none=True)
            for k, v in hc_updates.items():
                current = getattr(self.hard_constraints, k, None)
                if isinstance(v, list) and isinstance(current, list):
                    merged = list(dict.fromkeys(current + v))
                    if merged != current:
                        setattr(self.hard_constraints, k, merged)
                        updated.append(f"hard_constraints.{k}")
                elif current is None or current != v:
                    setattr(self.hard_constraints, k, v)
                    updated.append(f"hard_constraints.{k}")

        if update.soft_constraints is not None:
            sc_updates = update.soft_constraints.model_dump(exclude_none=True)
            for k, v in sc_updates.items():
                current = getattr(self.soft_constraints, k, None)
                if isinstance(v, list) and isinstance(current, list):
                    merged = list(dict.fromkeys(current + v))
                    if merged != current:
                        setattr(self.soft_constraints, k, merged)
                        updated.append(f"soft_constraints.{k}")
                elif current is None or current != v:
                    setattr(self.soft_constraints, k, v)
                    updated.append(f"soft_constraints.{k}")

        if update.confidence is not None and update.confidence != self.confidence:
            self.confidence = update.confidence
            updated.append("confidence")

        return updated


# ── Tool input model ───────────────────────────────────────


class UpdateExtractResultInput(BaseModel):
    """update_extract_result 工具输入 —— 增量更新 ExtractResult。

    LLM 每次只传本次对话新提取的字段。
    工具 handler 负责增量合并到已有 ExtractResult。
    """

    intent: UserIntent | None = Field(
        default=None, description="意图字段增量（只传本次新提取的字段）"
    )
    requirements: UserRequirements | None = Field(
        default=None, description="需求字段增量（list 会 merge 非覆盖）"
    )
    hard_constraints: HardConstraints | None = Field(
        default=None, description="硬约束字段增量（list 会 merge）"
    )
    soft_constraints: SoftConstraints | None = Field(
        default=None, description="软约束字段增量（list 会 merge）"
    )
    confidence: float | None = Field(
        default=None, description="当前提取置信度 0-1", ge=0.0, le=1.0
    )
