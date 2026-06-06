import { MapView } from "../../components/map/MapView"
import { PlanCard } from "../../components/plan/PlanCard"
import { ConfirmPanel } from "../../components/plan/ConfirmPanel"
import { QuestionPanel } from "../../components/plan/QuestionPanel"
import { BookingConfirmPanel } from "../../components/plan/BookingConfirmPanel"

export function PlanTab() {
  return (
    <div className="h-full flex">
      {/* Map 40% */}
      <div className="hidden md:block w-[40%] border-r border-zinc-800">
        <MapView />
      </div>
      {/* Plan detail 35% */}
      <div className="hidden md:block w-[35%] border-r border-zinc-800">
        <PlanCard />
      </div>
      {/* Confirm 25% */}
      <div className="flex-1 md:w-[25%] flex flex-col min-w-0">
        <div className="flex-1 min-h-0 overflow-auto p-4">
          <div className="text-xs text-zinc-500 space-y-2">
            <p>Send a plan request below to start.</p>
            <p>The agent pipeline will appear in the <strong className="text-zinc-400">Graph</strong> tab.</p>
            <p>Alerts and real-time context will appear in the <strong className="text-zinc-400">Monitor</strong> tab.</p>
            <p>Tool execution tracking is shown in the <strong className="text-zinc-400">Execution</strong> tab.</p>
          </div>
        </div>
        <QuestionPanel />
        <ConfirmPanel />
        <BookingConfirmPanel />
      </div>
    </div>
  )
}
