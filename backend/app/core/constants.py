"""核心常量 —— 状态枚举与策略参数。

枚举类型：
- PlanStatus: 7 状态 FSM（idle→done），其中 CONFIRMING 为可重入状态
- SceneType: 场景分类（family/friends/solo/date）
- POIType: POI 类型（restaurant/cafe/attraction/activity）
- ToolAction: Slot 动作类型（arrive/book_table/book_ticket/order）
- ExecutionStatus: Tool 执行状态（pending/running/success/failed/timeout/skipped）

策略参数：
- 超时控制: Intent 2s / Phase2 3s / Tool 3s / DAG 10s / Global 300s
- Fallback: 最大重试 2 次
- 共识: 确认超时 300s / 多数决比例 0.6 / 覆盖阈值 0.8

Author: SnapTrip Team
Date: 2026-05-13
"""

from enum import StrEnum


class PlanStatus(StrEnum):
    IDLE = "idle"
    DRAFTING = "drafting"
    PLANNING = "planning"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    DONE = "done"
    FAILED = "failed"


class SceneType(StrEnum):
    FAMILY = "family"
    FRIENDS = "friends"
    SOLO = "solo"
    DATE = "date"


class POIType(StrEnum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"


class ToolAction(StrEnum):
    ARRIVE = "arrive"
    BOOK_TABLE = "book_table"
    BOOK_TICKET = "book_ticket"
    ORDER = "order"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


# ===== 策略参数 =====

CONFIRM_TIMEOUT_S = 300
OVERRIDE_THRESHOLD = 0.8
FALLBACK_MAX_RETRY = 2
MAJORITY_RATIO = 0.6
EXEC_TIMEOUT_PER_TOOL_S = 3
EXEC_TIMEOUT_TOTAL_S = 10
INTENT_TIMEOUT_S = 2
CONTEXT_TIMEOUT_MS = 500
RETRIEVAL_TIMEOUT_S = 1
PLANNING_PHASE1_TIMEOUT_MS = 50
PLANNING_PHASE2_TIMEOUT_S = 3
FALLBACK_TIMEOUT_S = 2
NOTIFY_TIMEOUT_MS = 500
CONSENSUS_TIMEOUT_MS = 100
GLOBAL_TIMEOUT_S = 300
