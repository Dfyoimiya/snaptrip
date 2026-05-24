import { create } from "zustand"
import type { ConstraintEdge, PlanResponse, PlanSlot, SlotConfidence } from "../types/plan"
import type { ReplanTrigger } from "../types/agent"

interface PlanState {
  planId: string
  status: string
  slots: PlanSlot[]
  totalCost: number
  totalTimeMin: number
  shareCard: PlanResponse["share_card"]
  userInput: string
  error: string | null
  // v4
  constraintEdges: ConstraintEdge[]
  slotConfidences: Record<number, SlotConfidence>
  replanTrigger: ReplanTrigger | null

  setPlan: (plan: PlanResponse) => void
  setStatus: (status: string) => void
  setSlots: (slots: PlanSlot[]) => void
  setUserInput: (input: string) => void
  setConstraintEdges: (edges: ConstraintEdge[]) => void
  setSlotConfidences: (confidences: Record<number, SlotConfidence>) => void
  setReplanTrigger: (trigger: ReplanTrigger | null) => void
  reset: () => void
}

export const usePlanStore = create<PlanState>((set) => ({
  planId: "",
  status: "idle",
  slots: [],
  totalCost: 0,
  totalTimeMin: 0,
  shareCard: null,
  userInput: "",
  error: null,
  constraintEdges: [],
  slotConfidences: {},
  replanTrigger: null,

  setPlan: (plan) =>
    set({
      planId: plan.plan_id,
      status: plan.status,
      slots: plan.slots,
      totalCost: plan.total_cost,
      totalTimeMin: plan.total_time_min,
      shareCard: plan.share_card,
    }),

  setStatus: (status) => set({ status }),
  setSlots: (slots) => set({ slots }),
  setUserInput: (userInput) => set({ userInput }),
  setConstraintEdges: (edges) => set({ constraintEdges: edges }),
  setSlotConfidences: (confidences) => set({ slotConfidences: confidences }),
  setReplanTrigger: (trigger) => set({ replanTrigger: trigger }),

  reset: () =>
    set({
      planId: "",
      status: "idle",
      slots: [],
      totalCost: 0,
      totalTimeMin: 0,
      shareCard: null,
      userInput: "",
      error: null,
      constraintEdges: [],
      slotConfidences: {},
      replanTrigger: null,
    }),
}))
