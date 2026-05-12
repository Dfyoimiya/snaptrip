"""核心常量 —— 状态枚举 + 策略参数"""

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
