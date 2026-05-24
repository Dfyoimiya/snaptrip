import { create } from "zustand"
import type { Alert, MonitorPlan, RealTimeContext } from "../types/agent"

interface AlertState {
  alerts: Alert[]
  realtimeContext: RealTimeContext | null
  monitorPlan: MonitorPlan | null

  addAlert: (alert: Alert) => void
  setRealtimeContext: (ctx: RealTimeContext) => void
  setMonitorPlan: (plan: MonitorPlan) => void
  clearAlerts: () => void
  reset: () => void
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  realtimeContext: null,
  monitorPlan: null,

  addAlert: (alert) =>
    set((s) => ({
      alerts: [...s.alerts, { ...alert, timestamp: alert.timestamp ?? new Date().toISOString() }],
    })),

  setRealtimeContext: (ctx) => set({ realtimeContext: ctx }),
  setMonitorPlan: (plan) => set({ monitorPlan: plan }),
  clearAlerts: () => set({ alerts: [] }),
  reset: () => set({ alerts: [], realtimeContext: null, monitorPlan: null }),
}))
