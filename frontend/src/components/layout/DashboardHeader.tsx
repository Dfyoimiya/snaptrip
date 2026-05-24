import { RotateCcw } from "lucide-react"
import { useAgentStore } from "../../stores/agentStore"
import { usePlanStore } from "../../stores/planStore"
import { useAlertStore } from "../../stores/alertStore"
import type { AgentMode } from "../../stores/agentStore"

export function DashboardHeader() {
  const mode = useAgentStore((s) => s.mode)
  const setMode = useAgentStore((s) => s.setMode)
  const agentReset = useAgentStore((s) => s.reset)
  const planReset = usePlanStore((s) => s.reset)
  const alertReset = useAlertStore((s) => s.reset)

  function handleReset() {
    agentReset()
    planReset()
    alertReset()
  }

  return (
    <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-2">
        <span className="font-bold text-rose-400 text-sm">SnapTrip</span>
        <span className="text-xs text-zinc-600 hidden sm:inline">Agent Monitor</span>
      </div>

      <div className="flex items-center gap-2">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as AgentMode)}
          className="bg-zinc-800 text-xs text-zinc-300 px-2 py-1 rounded border border-zinc-700 outline-none focus:border-rose-500/50"
        >
          <option value="multi">Multi-Agent (10)</option>
          <option value="single">Single-Agent (6)</option>
        </select>

        <button
          onClick={handleReset}
          className="p-1.5 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          title="Reset all"
        >
          <RotateCcw size={14} />
        </button>
      </div>
    </div>
  )
}
