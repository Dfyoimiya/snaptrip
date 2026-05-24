import { useEffect } from "react"
import { sseUrl } from "../api/plan"
import { useAgentStore } from "../stores/agentStore"
import { usePlanStore } from "../stores/planStore"
import { useAlertStore } from "../stores/alertStore"
import type { SSEEvent, SSEPayload } from "../types/agent"

const EVENT_NODE_MAP: Record<string, string> = {
  intent: "intent_parser",
  retrieval: "retrieval_engine",
  planning: "planning_engine",
  planning_done: "planning_engine",
  consensus: "consensus_resolver",
  execution: "execution_engine",
  execution_done: "execution_engine",
  fallback: "fallback_engine",
  notify: "notify_engine",
  // v4
  context_loaded: "context_loader",
  memory_loaded: "memory_manager",
  monitor: "monitor_engine",
  alert: "monitor_engine",
  replan: "planning_engine",
}

export function usePlanSSE(planId: string | null) {
  const addLog = useAgentStore((s) => s.addLog)
  const updateNode = useAgentStore((s) => s.updateNode)
  const setRunning = useAgentStore((s) => s.setRunning)
  const setAwaitingConfirm = useAgentStore((s) => s.setAwaitingConfirm)
  const setExecutionState = useAgentStore((s) => s.setExecutionState)
  const setStatus = usePlanStore((s) => s.setStatus)
  const setReplanTrigger = usePlanStore((s) => s.setReplanTrigger)
  const addAlert = useAlertStore((s) => s.addAlert)
  const setRealtimeContext = useAlertStore((s) => s.setRealtimeContext)
  const setMonitorPlan = useAlertStore((s) => s.setMonitorPlan)

  useEffect(() => {
    if (!planId) return

    const es = new EventSource(sseUrl(planId))
    setRunning(true)

    es.onmessage = (e) => {
      try {
        const raw = JSON.parse(e.data)
        const eventName: SSEEvent = raw.event ?? e.type
        const payload: SSEPayload = typeof raw.data === "string" ? JSON.parse(raw.data) : raw

        addLog(eventName, payload)

        // Update pipeline node status
        const nodeId = EVENT_NODE_MAP[eventName]
        if (nodeId) {
          if (eventName.endsWith("_done")) {
            updateNode(nodeId, "done")
          } else {
            updateNode(nodeId, "running")
          }
        }

        // v4: Multi-store dispatch based on event type
        switch (eventName) {
          case "planning_done":
            setStatus("confirming")
            break
          case "consensus":
            setAwaitingConfirm(true)
            break
          case "execution_done":
            setStatus("executing")
            if (payload.execution_state) {
              setExecutionState(payload.execution_state)
            }
            break
          case "done":
            setRunning(false)
            setStatus("done")
            break
          case "alert":
            if (payload.alerts) {
              payload.alerts.forEach((a) => addAlert(a))
            }
            break
          case "monitor":
            if (payload.realtime_context) {
              setRealtimeContext(payload.realtime_context)
            }
            break
          case "replan":
            updateNode("planning_engine", "running")
            if (payload.replan_trigger) {
              setReplanTrigger(payload.replan_trigger)
            }
            break
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      setRunning(false)
      es.close()
    }

    return () => {
      es.close()
      setRunning(false)
    }
  }, [planId, addLog, updateNode, setRunning, setAwaitingConfirm, setStatus,
      setExecutionState, setReplanTrigger, addAlert, setRealtimeContext, setMonitorPlan])
}
