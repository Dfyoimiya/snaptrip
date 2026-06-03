// 后端 Schema 对应的前端类型定义
// 与 backend/app/schemas/plan.py 对齐

export interface TimeRange {
  start: string
  end: string
}

export interface POI {
  id: string
  name: string
  city: string
  type: string
  lat: number
  lng: number
  mood_tags: string[]
  avg_price: number
  rating: number
}

export interface SlotAlternative {
  poi_id: string
  prechecked: boolean
  score: number
}

export interface PlanSlot {
  sequence: number
  poi: POI
  time_range: TimeRange
  action: string
  estimated_cost: number
  move_time_min: number
  confidence: number
  shadow_id?: string
  rationale?: string[]
  alternatives?: SlotAlternative[]
}

export interface ConstraintEdge {
  from_slot: number
  to_slot: number
  constraint_type: "travel_time" | "budget_cascade" | "time_window" | "type_diversity"
  min_value: number
  max_value: number
  current_value: number
}

export interface SlotConfidence {
  overall: number
  availability_confidence: number
  route_confidence: number
  pricing_confidence: number
  weather_confidence: number
}

export interface ShareCard {
  url: string
  message: string
}

export interface PlanResponse {
  plan_id: string
  query_text: string
  status: string
  total_cost: number
  total_time_min: number
  slots: PlanSlot[]
  share_card: ShareCard | null
}

export interface PlanCreateRequest {
  user_input: string
  user_id?: string
  lat?: number
  lng?: number
}

export interface ConfirmRequest {
  decision: string
  slot_index?: number
  locked_slots?: number[]
  rejected_slots?: number[]
  modification_instructions?: string
  replace_only?: boolean
  change_requests?: Array<{
    slot_index?: number
    instruction?: string
    replace_only?: boolean
  }>
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}
