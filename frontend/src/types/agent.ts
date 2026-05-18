// SSE 事件类型 + Agent 状态

export type SSEEvent =
  | "intent"
  | "retrieval"
  | "planning"
  | "planning_done"
  | "consensus"
  | "execution"
  | "execution_done"
  | "fallback"
  | "notify"
  | "done"

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
}

export interface AgentNode {
  id: string
  label: string
  status: "idle" | "running" | "done" | "error"
  elapsed_ms?: number
  output?: string
}

export type AgentPipeline = AgentNode[]
