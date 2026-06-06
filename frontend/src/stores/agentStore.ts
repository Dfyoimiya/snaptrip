import { create } from "zustand"
import type { InterruptPayload } from "../types/agent"

interface AgentState {
  isRunning: boolean
  interruptPayload: InterruptPayload | null

  setRunning: (v: boolean) => void
  setInterruptPayload: (payload: InterruptPayload | null) => void
  reset: () => void
}

export const useAgentStore = create<AgentState>((set) => ({
  isRunning: false,
  interruptPayload: null,

  setRunning: (v) => set({ isRunning: v }),
  setInterruptPayload: (payload) => set({ interruptPayload: payload }),
  reset: () => set({ isRunning: false, interruptPayload: null }),
}))
