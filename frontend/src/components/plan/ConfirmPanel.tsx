import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"

export function ConfirmPanel() {
  const planId = usePlanStore((s) => s.planId)
  const awaitingConfirm = useAgentStore((s) => s.awaitingConfirm)
  const setAwaitingConfirm = useAgentStore((s) => s.setAwaitingConfirm)
  const setPlan = usePlanStore((s) => s.setPlan)

  if (!awaitingConfirm) return null

  async function handleConfirm(decision: string) {
    setAwaitingConfirm(false)
    try {
      const resp = await confirmPlan(planId, { decision })
      if (resp.code === 0 && resp.data) {
        setPlan(resp.data)
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="mx-4 mb-3 p-3 rounded-lg bg-zinc-800 border border-zinc-700">
      <p className="text-xs text-zinc-300 mb-2">确认这个计划吗？</p>
      <div className="flex gap-2">
        <button
          className="flex-1 py-1.5 text-xs rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
          onClick={() => handleConfirm("confirmed")}
        >
          确认 ✓
        </button>
        <button
          className="flex-1 py-1.5 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
          onClick={() => handleConfirm("objection")}
        >
          换一个
        </button>
      </div>
    </div>
  )
}
