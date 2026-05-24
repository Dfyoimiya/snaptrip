import { create } from "zustand"
import type { AgentNode, ExecutionState, SSEEvent, SSEPayload } from "../types/agent"

export type AgentMode = "multi" | "single"

interface AgentState {
  nodes: AgentNode[]
  logs: string[]
  isRunning: boolean
  awaitingConfirm: boolean
  mode: AgentMode
  executionState: ExecutionState | null

  addLog: (evt: SSEEvent, payload: SSEPayload) => void
  updateNode: (id: string, status: AgentNode["status"]) => void
  setRunning: (v: boolean) => void
  setAwaitingConfirm: (v: boolean) => void
  setMode: (mode: AgentMode) => void
  setExecutionState: (state: ExecutionState) => void
  reset: () => void
}

const PIPELINE_MULTI: AgentNode[] = [
  { id: "intent_parser",       label: "意图解析",   status: "idle", layer: 0 },
  { id: "context_loader",      label: "上下文加载", status: "idle", layer: 1 },
  { id: "memory_manager",      label: "记忆管理",   status: "idle", layer: 1 },
  { id: "retrieval_engine",    label: "POI 检索",   status: "idle", layer: 2 },
  { id: "planning_engine",     label: "智能规划",   status: "idle", layer: 3 },
  { id: "consensus_resolver",  label: "等待确认",   status: "idle", layer: 4 },
  { id: "execution_engine",    label: "预订执行",   status: "idle", layer: 5 },
  { id: "fallback_engine",     label: "异常容错",   status: "idle", layer: 5 },
  { id: "notify_engine",       label: "生成卡片",   status: "idle", layer: 5 },
  { id: "monitor_engine",      label: "实时监控",   status: "idle", layer: 6 },
]

const PIPELINE_SINGLE: AgentNode[] = [
  { id: "planner",             label: "智能规划",   status: "idle", layer: 0 },
  { id: "consensus",           label: "等待确认",   status: "idle", layer: 1 },
  { id: "execution",           label: "预订执行",   status: "idle", layer: 2 },
  { id: "fallback",            label: "异常容错",   status: "idle", layer: 2 },
  { id: "notify",              label: "生成卡片",   status: "idle", layer: 2 },
  { id: "monitor",             label: "实时监控",   status: "idle", layer: 3 },
]

function initNodes(mode: AgentMode): AgentNode[] {
  return (mode === "single" ? PIPELINE_SINGLE : PIPELINE_MULTI).map((n) => ({ ...n }))
}

export const useAgentStore = create<AgentState>((set) => ({
  nodes: initNodes("multi"),
  logs: [],
  isRunning: false,
  awaitingConfirm: false,
  mode: "multi",
  executionState: null,

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

  setMode: (mode) =>
    set({
      mode,
      nodes: initNodes(mode),
      logs: [],
      executionState: null,
    }),

  setExecutionState: (state) => set({ executionState: state }),

  reset: () =>
    set((s) => ({
      nodes: initNodes(s.mode),
      logs: [],
      isRunning: false,
      awaitingConfirm: false,
      executionState: null,
    })),
}))
