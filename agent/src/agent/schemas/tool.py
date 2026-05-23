"""Tool Schema —— Tool 调用契约、注册表与定义。

定义 Hermes Agent 兼容的工具调用协议：
- ToolInvocation: 单次工具调用请求
- ToolResult: 工具调用结果
- ToolDefinition: 工具元数据定义 (含 JSON Schema)
- TOOL_REGISTRY: 10 个工具注册表

Tool DAG 分层:
  L0: search_poi / get_user_profile          —— 无依赖，可并行
  L1: check_queue / check_availability       —— 依赖 search_poi
      check_child_facility / calculate_route
  L2: book_table / book_ticket / order       —— 依赖 L1 结果
  L3: notify                                 —— 依赖 L2 全部完成

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

# ===== 调用模型 =====


class ToolInvocation(BaseModel):
    """单次工具调用请求"""

    tool_name: str
    invocation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = 5000
    dependencies: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    """工具调用结果"""

    invocation_id: str
    status: Literal["success", "failure", "timeout", "degraded"] = "success"
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0


# ===== 工具定义 =====


class ToolDefinition(BaseModel):
    """工具元数据定义 —— JSON Schema 参数/输出校验。

    LLM 可见字段: name, human_readable_name, llm_description, input_schema, output_schema
    ExecutionEngine 专用: layer, dependencies, is_idempotent, fallback_policy, physical_impact
    """

    name: str
    human_readable_name: str = ""  # LLM 可见: "预订餐厅桌位"
    llm_description: str = ""  # LLM 可见: 自然语言描述工具用途与注意事项
    description: str  # 简短描述
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    layer: int = 0  # DAG 层级（LLM 不可见）
    dependencies: list[str] = Field(default_factory=list)  # DAG 依赖（LLM 不可见）
    is_idempotent: bool = True  # ExecutionEngine 使用
    default_timeout_ms: int = 3000
    fallback_policy: Literal["abort", "degrade", "continue"] = (
        "abort"  # ExecutionEngine 使用
    )
    physical_impact: bool = False  # 标记物理操作（LLM 不可见）


# ===== Tool 注册表 =====

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "search_poi": ToolDefinition(
        name="search_poi",
        human_readable_name="搜索兴趣点",
        llm_description="搜索指定城市内的兴趣点(POI)，可按类别、坐标、半径过滤。返回POI列表含名称、类型、评分、价格、亲子设施等信息。这是所有本地生活规划的第一步。",
        description="搜索兴趣点 (POI)，支持按城市、类别、坐标半径过滤",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"},
                "category": {"type": "string", "description": "POI 类别"},
                "lat": {"type": "number", "description": "中心纬度"},
                "lng": {"type": "number", "description": "中心经度"},
                "radius_km": {
                    "type": "number",
                    "description": "搜索半径(km)",
                    "default": 15,
                },
            },
            "required": ["city"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "pois": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer"},
            },
        },
        layer=0,
        is_idempotent=True,
        default_timeout_ms=1500,
        fallback_policy="degrade",
    ),
    "get_user_profile": ToolDefinition(
        name="get_user_profile",
        human_readable_name="获取用户画像",
        llm_description="获取当前用户的偏好画像与历史行为向量，包含饮食偏好、出行风格、历史拒绝记录等。用于个性化推荐。",
        description="获取用户画像与偏好向量",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
            },
            "required": ["user_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "preferences": {"type": "object"},
                "travel_style": {"type": "string"},
                "preference_embedding": {"type": "array", "items": {"type": "number"}},
            },
        },
        layer=0,
        is_idempotent=True,
        default_timeout_ms=500,
        fallback_policy="degrade",
    ),
    "check_queue": ToolDefinition(
        name="check_queue",
        human_readable_name="查询排队情况",
        llm_description="查询指定POI的当前排队人数和预计等待时间。用于评估是否需要提前预订或调整时间。",
        description="查询 POI 排队情况",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
                "guest_count": {"type": "integer"},
            },
            "required": ["poi_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "queue_length": {"type": "integer"},
                "wait_minutes": {"type": "integer"},
            },
        },
        layer=1,
        dependencies=["search_poi"],
        is_idempotent=True,
        default_timeout_ms=1000,
        fallback_policy="degrade",
    ),
    "check_availability": ToolDefinition(
        name="check_availability",
        human_readable_name="查询可用时段",
        llm_description=(
            "查询指定POI在给定时间范围内是否有可用时段/座位/库存。"
            "调用 book_table 或 book_ticket 之前必须先调用此工具确认可用性。"
        ),
        description="查询 POI 可用时段",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
                "time_range": {"type": "string"},
            },
            "required": ["poi_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "available": {"type": "boolean"},
                "next_available": {"type": "string"},
            },
        },
        layer=1,
        dependencies=["search_poi"],
        is_idempotent=True,
        default_timeout_ms=1000,
        fallback_policy="degrade",
    ),
    "check_child_facility": ToolDefinition(
        name="check_child_facility",
        human_readable_name="查询亲子设施",
        llm_description="查询指定POI的亲子友好设施：是否有母婴室、儿童座椅、儿童菜单等。带小孩出行时建议调用。",
        description="查询 POI 亲子设施（母婴室、儿童座椅等）",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
            },
            "required": ["poi_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "has_nursing_room": {"type": "boolean"},
                "has_child_seat": {"type": "boolean"},
            },
        },
        layer=1,
        dependencies=["search_poi"],
        is_idempotent=True,
        default_timeout_ms=800,
        fallback_policy="degrade",
    ),
    "calculate_route": ToolDefinition(
        name="calculate_route",
        human_readable_name="计算路线",
        llm_description="计算两点之间的路线距离和通行时间，支持步行、驾车、公交三种出行方式。用于评估POI间移动时间是否合理。",
        description="计算两点间路线与通行时间",
        input_schema={
            "type": "object",
            "properties": {
                "from_lat": {"type": "number"},
                "from_lng": {"type": "number"},
                "to_lat": {"type": "number"},
                "to_lng": {"type": "number"},
                "mode": {"type": "string", "enum": ["walking", "driving", "transit"]},
            },
            "required": ["from_lat", "from_lng", "to_lat", "to_lng"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "distance_km": {"type": "number"},
                "duration_min": {"type": "integer"},
            },
        },
        layer=1,
        dependencies=["search_poi"],
        is_idempotent=True,
        default_timeout_ms=800,
        fallback_policy="degrade",
    ),
    "book_table": ToolDefinition(
        name="book_table",
        human_readable_name="预订餐厅桌位",
        llm_description=(
            "预订指定餐厅的桌位。调用前必须先通过 check_availability 确认有空位。"
            "参数 time_slot 使用 HH:MM 格式（如 19:00），guest_count 为实际就餐人数。"
            "预订成功后桌位将锁定，超时自动释放。此操作影响餐厅真实库存，不可随意重试。"
        ),
        description="预订餐厅桌位",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
                "guest_count": {"type": "integer"},
                "time_slot": {"type": "string"},
            },
            "required": ["poi_id", "guest_count", "time_slot"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "booking_id": {"type": "string"},
                "table_number": {"type": "string"},
            },
        },
        layer=2,
        dependencies=["check_queue", "check_availability"],
        is_idempotent=False,
        default_timeout_ms=2000,
        fallback_policy="abort",
        physical_impact=True,
    ),
    "book_ticket": ToolDefinition(
        name="book_ticket",
        human_readable_name="预订门票",
        llm_description=(
            "预订景点或活动门票。调用前必须先通过 check_availability 确认有余票。"
            "参数包含POI ID、人数、日期。预订成功后门票库存扣减，此操作影响真实库存，不可随意重试。"
        ),
        description="预订景点/活动门票",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
                "guest_count": {"type": "integer"},
                "date": {"type": "string"},
            },
            "required": ["poi_id", "guest_count"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "booking_id": {"type": "string"},
                "ticket_count": {"type": "integer"},
            },
        },
        layer=2,
        dependencies=["check_availability"],
        is_idempotent=False,
        default_timeout_ms=2000,
        fallback_policy="degrade",
        physical_impact=True,
    ),
    "order": ToolDefinition(
        name="order",
        human_readable_name="下单点餐",
        llm_description=(
            "在指定POI下单点餐或购物。参数包含POI ID和菜品/商品列表。"
            "下单后将触发厨房备餐或商家拣货，此操作产生真实物理影响（备餐/库存），不可重试。"
        ),
        description="下单点餐/购物",
        input_schema={
            "type": "object",
            "properties": {
                "poi_id": {"type": "string"},
                "items": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["poi_id", "items"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "total_price": {"type": "number"},
            },
        },
        layer=2,
        dependencies=["search_poi"],
        is_idempotent=False,
        default_timeout_ms=1500,
        fallback_policy="continue",
        physical_impact=True,
    ),
    "notify": ToolDefinition(
        name="notify",
        human_readable_name="发送通知",
        llm_description="向用户发送计划确认通知和分享卡片，支持微信、短信、邮件三种渠道。在所有预订完成后调用。",
        description="发送计划通知与分享卡片",
        input_schema={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "channel": {"type": "string", "enum": ["wechat", "sms", "email"]},
            },
            "required": ["plan_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "sent": {"type": "boolean"},
                "share_url": {"type": "string"},
            },
        },
        layer=3,
        dependencies=["book_table", "book_ticket", "order"],
        is_idempotent=True,
        default_timeout_ms=1000,
        fallback_policy="continue",
    ),
}
