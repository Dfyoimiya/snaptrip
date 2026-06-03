import { useCallback, useState } from "react"
import { createPlan } from "../api/plan"
import { InputBar } from "../components/common/InputBar"
import { DashboardHeader } from "../components/layout/DashboardHeader"
import { DashboardTabs, type TabId } from "../components/layout/DashboardTabs"
import { ErrorBoundary } from "../components/layout/ErrorBoundary"
import { PlanTab } from "./tabs/PlanTab"
import { GraphTab } from "./tabs/GraphTab"
import { MonitorTab } from "./tabs/MonitorTab"
import { ExecutionTab } from "./tabs/ExecutionTab"
import { DebugTab } from "./tabs/DebugTab"
import { usePlanSSE } from "../hooks/usePlanSSE"
import { useGeolocation } from "../hooks/useGeolocation"
import { useAgentStore } from "../stores/agentStore"
import { usePlanStore } from "../stores/planStore"
import { useAlertStore } from "../stores/alertStore"
import type { PlanCreateRequest, PlanResponse } from "../types/plan"

export function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>("plan")
  const [loading, setLoading] = useState(false)
  const geo = useGeolocation()

  const planId = usePlanStore((s) => s.planId)
  const setPlan = usePlanStore((s) => s.setPlan)
  const setUserInput = usePlanStore((s) => s.setUserInput)
  const agentReset = useAgentStore((s) => s.reset)
  const planReset = usePlanStore((s) => s.reset)
  const alertReset = useAlertStore((s) => s.reset)
  const setRunning = useAgentStore((s) => s.setRunning)

  usePlanSSE(loading ? planId : null)

  const handleSend = useCallback(
    async (text: string) => {
      setLoading(true)
      agentReset()
      planReset()
      alertReset()
      setUserInput(text)
      setRunning(true)

      try {
        const req: PlanCreateRequest = { user_input: text }
        if (geo.lat !== null && geo.lng !== null) {
          req.lat = geo.lat
          req.lng = geo.lng
        }
        const resp = await createPlan(req)
        const data = resp.data ?? resp
        if (data && data.slots) {
          setPlan(data as PlanResponse)
        }
      } catch {
        // ignore
      } finally {
        setLoading(false)
        setRunning(false)
      }
    },
    [setPlan, setUserInput, agentReset, planReset, alertReset, setRunning],
  )

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100">
      <DashboardHeader />
      <DashboardTabs active={activeTab} onSelect={setActiveTab} />

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ErrorBoundary fallback="Plan tab error">
          {activeTab === "plan" && <PlanTab />}
        </ErrorBoundary>
        <ErrorBoundary fallback="Graph tab error">
          {activeTab === "graph" && <GraphTab />}
        </ErrorBoundary>
        <ErrorBoundary fallback="Monitor tab error">
          {activeTab === "monitor" && <MonitorTab />}
        </ErrorBoundary>
        <ErrorBoundary fallback="Execution tab error">
          {activeTab === "execution" && <ExecutionTab />}
        </ErrorBoundary>
        <ErrorBoundary fallback="Debug tab error">
          {activeTab === "debug" && <DebugTab />}
        </ErrorBoundary>
      </div>

      <InputBar onSend={handleSend} disabled={loading} />
    </div>
  )
}
