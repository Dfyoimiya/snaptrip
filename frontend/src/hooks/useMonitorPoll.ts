import { useEffect, useRef } from "react"
import { getPlan } from "../api/plan"
import { useAlertStore } from "../stores/alertStore"

/**
 * Polls /api/v1/plan/{planId} for v4 monitoring data when SSE is disconnected
 * or doesn't carry the full v4 payload.
 *
 * Poll interval: 5s when active
 */
export function useMonitorPoll(planId: string | null, sseActive: boolean) {
  const setRealtimeContext = useAlertStore((s) => s.setRealtimeContext)
  const addAlert = useAlertStore((s) => s.addAlert)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    // Only poll when SSE is not active and we have a plan
    if (!planId || sseActive) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    const poll = async () => {
      try {
        const resp = await getPlan(planId)
        const plan = resp.data ?? resp

        // Extract v4 fields from plan response (backend may or may not include them)
        if (plan) {
          const p = plan as any
          // Check if the plan response carries v4 monitoring data
          if (p.realtime_context) {
            setRealtimeContext(p.realtime_context)
          }
          if (p.alerts) {
            for (const a of p.alerts) {
              addAlert(a)
            }
          }
          if (p.monitor_plan) {
            useAlertStore.getState().setMonitorPlan(p.monitor_plan)
          }
        }
      } catch {
        // silently ignore poll errors
      }
    }

    poll() // immediate first poll
    intervalRef.current = setInterval(poll, 5_000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [planId, sseActive, setRealtimeContext, addAlert])
}
