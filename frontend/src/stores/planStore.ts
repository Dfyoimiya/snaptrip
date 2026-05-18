import { create } from "zustand"
import type { PlanResponse, PlanSlot } from "../types/plan"

interface PlanState {
  planId: string
  status: string
  slots: PlanSlot[]
  totalCost: number
  totalTimeMin: number
  shareCard: PlanResponse["share_card"]
  userInput: string
  error: string | null

  setPlan: (plan: PlanResponse) => void
  setStatus: (status: string) => void
  setSlots: (slots: PlanSlot[]) => void
  setUserInput: (input: string) => void
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
    }),
}))
