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

export interface PlanSlot {
  sequence: number
  poi: POI
  time_range: TimeRange
  action: string
  estimated_cost: number
  move_time_min: number
  confidence: number
  shadow_id?: string
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
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}
