// SSE 事件类型 + Agent 状态 + v4 实时监控

export type SSEEvent =
  | "intent" | "retrieval" | "planning" | "planning_done"
  | "consensus" | "execution" | "execution_done"
  | "fallback" | "notify" | "done"
  | "context_loaded" | "memory_loaded"
  | "monitor" | "alert" | "replan"
  // v5 HITL interrupt events
  | "question" | "need_confirmation" | "confirm_booking"

export interface SSEPayload {
  plan_id: string
  node?: string
  status: string
  candidates?: number
  slots?: number
  total_cost?: number
  failed_count?: number
  tool?: string
  poi_name?: string
  card_url?: string
  // v4
  alerts?: Alert[]
  execution_state?: ExecutionState
  realtime_context?: RealTimeContext
  replan_trigger?: ReplanTrigger
}

// ===== Agent Pipeline =====

export interface AgentNode {
  id: string
  label: string
  status: "idle" | "running" | "done" | "error"
  layer: number
  elapsed_ms?: number
  output?: string
}

// ===== v4 Real-Time Context =====

export interface WeatherSnapshot {
  condition: "sunny" | "cloudy" | "rainy" | "snowy" | "stormy"
  temperature_c: number
  outdoor_score: number
  report_time: string
}

export interface TrafficIndex {
  overall: number
  by_corridor: Record<string, number>
}

export interface PeakCalendar {
  hourly_multipliers: Record<number, number>
  special_events: string[]
}

export interface RealTimeContext {
  weather: WeatherSnapshot | null
  traffic_index: TrafficIndex | null
  peak_calendar: PeakCalendar | null
}

// ===== Alerts =====

export type AlertType =
  | "traffic_delay" | "queue_surge" | "weather_change"
  | "booking_cancelled" | "poi_closed"

export type AlertSeverity = "info" | "warning" | "critical"

export interface Alert {
  alert_type: AlertType
  severity: AlertSeverity
  slot_indices: number[]
  message: string
  suggested_action: "no_op" | "partial_replan" | "full_replan" | "cancel"
  timestamp?: string
}

// ===== Execution Tracking =====

export interface ToolExecutionRecord {
  invocation_id: string
  slot_index: number
  tool_name: string
  layer: number
  status: "success" | "failure" | "timeout" | "skipped"
  error_code?: string
  error_message?: string
  booking_id?: string
  latency_ms: number
  depends_on: string[]
}

export interface ExecutionState {
  run_id: string
  status: "full_success" | "partial_success" | "full_failure"
  tool_records: ToolExecutionRecord[]
  confirmed_bookings: Record<number, string>
  failed_slot_indices: number[]
  total_elapsed_ms: number
}

export interface ReplanTrigger {
  scope: "partial" | "full"
  affected_slot_indices: number[]
  recommended_alternatives: string[]
  auto_replan: boolean
}

// ===== HITL Interrupt =====

export type InterruptType = "question" | "plan_confirm" | "booking_confirm"

export interface OptionItem {
  label: string
  /** 选项值（不填则等于 label） */
  value: string
  /** 选项描述/副标题 */
  description?: string | null
}

export interface PlanSlot {
  time_start?: string
  time_end?: string
  action?: string
  place?: string
  estimated_cost?: number
  note?: string
}

export interface PlanData {
  summary?: string
  total_cost?: number
  slots?: PlanSlot[]
}

export interface BookingOrderItem {
  order_type: string       // restaurant/activity/cake/flowers
  poi_name: string
  guest_count: number
  time?: string | null
  amount_cny: number
  note?: string | null
}

export interface BookingData {
  orders?: BookingOrderItem[]
  total_amount?: number
}

export interface InterruptPayload {
  type: InterruptType
  message: string
  /** 选项卡片列表（匹配后端 OptionItem） */
  options: OptionItem[]
  plan?: PlanData | null
  booking?: BookingData | null
}

export interface PipelineNodeData extends Record<string, unknown> {
  label: string
  status: AgentNode["status"]
  layer: number
  type: "engine" | "checkpoint" | "monitor"
}

export interface ToolNodeData extends Record<string, unknown> {
  name: string
  human_readable_name: string
  layer: number
  status: "pending" | "running" | "success" | "failure" | "skipped"
  is_idempotent: boolean
  physical_impact: boolean
  latency_ms?: number
}

// ===== Monitor Plan =====

export interface RouteCheck {
  from_slot: number
  to_slot: number
  baseline_travel_min: number
  current_travel_min?: number
}

export interface QueueCheck {
  slot_index: number
  poi_id: string
  baseline_queue: number
  current_queue?: number
}

export interface BookingCheck {
  slot_index: number
  poi_id: string
  booking_id: string
  current_status?: string
}

export interface MonitorPlan {
  poll_interval_s: number
  routes_to_track: RouteCheck[]
  queues_to_track: QueueCheck[]
  bookings_to_track: BookingCheck[]
  deadline?: string
}

// ===== Tool Registry (前端映射) =====

export interface ToolDef {
  name: string
  human_readable_name: string
  layer: number
  dependencies: string[]
  is_idempotent: boolean
  physical_impact: boolean
}

export const TOOL_REGISTRY: Record<string, ToolDef> = {
  search_poi:          { name: "search_poi",          human_readable_name: "搜索兴趣点",   layer: 0, dependencies: [],                           is_idempotent: true,  physical_impact: false },
  get_user_profile:    { name: "get_user_profile",    human_readable_name: "获取用户画像",   layer: 0, dependencies: [],                           is_idempotent: true,  physical_impact: false },
  get_weather:         { name: "get_weather",         human_readable_name: "查询实时天气",   layer: 0, dependencies: [],                           is_idempotent: true,  physical_impact: false },
  get_traffic_index:   { name: "get_traffic_index",   human_readable_name: "查询实时交通",   layer: 0, dependencies: [],                           is_idempotent: true,  physical_impact: false },
  get_peak_hours:      { name: "get_peak_hours",      human_readable_name: "查询高峰时段",   layer: 0, dependencies: [],                           is_idempotent: true,  physical_impact: false },
  check_queue:         { name: "check_queue",         human_readable_name: "查询排队情况",   layer: 1, dependencies: ["search_poi"],               is_idempotent: true,  physical_impact: false },
  check_availability:  { name: "check_availability",  human_readable_name: "查询可用时段",   layer: 1, dependencies: ["search_poi"],               is_idempotent: true,  physical_impact: false },
  check_child_facility:{ name: "check_child_facility",human_readable_name: "查询亲子设施",   layer: 1, dependencies: ["search_poi"],               is_idempotent: true,  physical_impact: false },
  calculate_route:     { name: "calculate_route",     human_readable_name: "计算路线",      layer: 1, dependencies: ["search_poi"],               is_idempotent: true,  physical_impact: false },
  book_table:          { name: "book_table",          human_readable_name: "预订餐厅桌位",   layer: 2, dependencies: ["check_queue","check_availability"], is_idempotent: false, physical_impact: true },
  book_ticket:         { name: "book_ticket",         human_readable_name: "预订门票",      layer: 2, dependencies: ["check_availability"],        is_idempotent: false, physical_impact: true },
  order:               { name: "order",               human_readable_name: "下单点餐",      layer: 2, dependencies: ["search_poi"],               is_idempotent: false, physical_impact: true },
  modify_booking:      { name: "modify_booking",      human_readable_name: "修改预订",      layer: 2, dependencies: ["book_table","book_ticket"], is_idempotent: false, physical_impact: true },
  cancel_booking:      { name: "cancel_booking",      human_readable_name: "取消预订",      layer: 2, dependencies: ["book_table","book_ticket"], is_idempotent: true,  physical_impact: true },
  notify:              { name: "notify",              human_readable_name: "发送通知",      layer: 3, dependencies: ["book_table","book_ticket","order"], is_idempotent: true, physical_impact: false },
  track_booking_status:{ name: "track_booking_status",human_readable_name: "查询预订状态",   layer: 3, dependencies: ["book_table","book_ticket","order","modify_booking","cancel_booking"], is_idempotent: true, physical_impact: false },
  check_plan_progress: { name: "check_plan_progress", human_readable_name: "查询计划进度",   layer: 3, dependencies: ["book_table","book_ticket","order","modify_booking","cancel_booking"], is_idempotent: true, physical_impact: false },
}
