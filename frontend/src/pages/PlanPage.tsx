import { useCallback, useState } from "react"
import { createPlan } from "../api/plan"
import { AgentMonitor } from "../components/agent/AgentMonitor"
import { InputBar } from "../components/common/InputBar"
import { MapView } from "../components/map/MapView"
import { ConfirmPanel } from "../components/plan/ConfirmPanel"
import { QuestionPanel } from "../components/plan/QuestionPanel"
import { BookingConfirmPanel } from "../components/plan/BookingConfirmPanel"
import { PlanCard } from "../components/plan/PlanCard"
import { usePlanSSE } from "../hooks/usePlanSSE"
import { useGeolocation } from "../hooks/useGeolocation"
import { useAgentStore } from "../stores/agentStore"
import { usePlanStore } from "../stores/planStore"
import type { PlanCreateRequest, PlanResponse } from "../types/plan"

export function PlanPage() {
  const [loading, setLoading] = useState(false)
  const geo = useGeolocation()
  const planId = usePlanStore((s) => s.planId)
  const setPlan = usePlanStore((s) => s.setPlan)
  const setUserInput = usePlanStore((s) => s.setUserInput)
  const reset = usePlanStore((s) => s.reset)
  const agentReset = useAgentStore((s) => s.reset)
  const setRunning = useAgentStore((s) => s.setRunning)

  usePlanSSE(loading ? planId : null)

  const handleSend = useCallback(
    async (text: string) => {
      setLoading(true)
      agentReset()
      reset()
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
    [setPlan, setUserInput, reset, agentReset, setRunning],
  )

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100">
      {/* header */}
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2">
        <span className="font-bold text-rose-400 text-sm">SnapTrip</span>
        <span className="text-xs text-zinc-600">本地生活智能规划 Agent</span>
      </div>

      {/* three-column body */}
      <div className="flex-1 flex min-h-0">
        {/* left: map 40% */}
        <div className="hidden md:block w-[40%] border-r border-zinc-800">
          <MapView />
        </div>

        {/* center: agent brain 35% */}
        <div className="hidden md:block w-[35%] border-r border-zinc-800">
          <AgentMonitor />
        </div>

        {/* right: plan card + confirm 25% */}
        <div className="flex-1 md:w-[25%] flex flex-col min-w-0">
          <div className="flex-1 min-h-0 overflow-auto">
            <PlanCard />
          </div>
          <QuestionPanel />
          <ConfirmPanel />
          <BookingConfirmPanel />
        </div>
      </div>

      {/* input bar */}
      <InputBar onSend={handleSend} disabled={loading} />
    </div>
  )
}
