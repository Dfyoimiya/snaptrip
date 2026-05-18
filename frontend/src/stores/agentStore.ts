import { create } from "zustand"
import type { AgentNode, SSEEvent, SSEPayload } from "../types/agent"

interface AgentState {
  nodes: AgentNode[]
  logs: string[]
  isRunning: boolean
  awaitingConfirm: boolean

  addLog: (evt: SSEEvent, payload: SSEPayload) => void
  updateNode: (id: string, status: AgentNode["status"]) => void
  setRunning: (v: boolean) => void
  setAwaitingConfirm: (v: boolean) => void
  reset: () => void
}

const PIPELINE: AgentNode[] = [
  { id: "intent_parser", label: "意图解析", status: "idle" },
  { id: "retrieval_engine", label: "POI 检索", status: "idle" },
  { id: "planning_engine", label: "智能规划", status: "idle" },
  { id: "consensus_resolver", label: "等待确认", status: "idle" },
  { id: "execution_engine", label: "预订执行", status: "idle" },
  { id: "fallback_engine", label: "异常容错", status: "idle" },
  { id: "notify_engine", label: "生成卡片", status: "idle" },
]

export const useAgentStore = create<AgentState>((set, get) => ({
  nodes: PIPELINE.map((n) => ({ ...n })),
  logs: [],
  isRunning: false,
  awaitingConfirm: false,

  addLog: (evt, payload) => {
    const msg = JSON.stringify({ event: evt, ...payload })
    set((s) => ({ logs: [...s.logs, msg] }))
  },

  updateNode: (id, status) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, status } : n)),
    })),

  setRunning: (v) => set({ isRunning: v }),
  setAwaitingConfirm: (v) => set({ awaitingConfirm: v }),

  reset: () =>
    set({
      nodes: PIPELINE.map((n) => ({ ...n })),
      logs: [],
      isRunning: false,
      awaitingConfirm: false,
    }),
}))
