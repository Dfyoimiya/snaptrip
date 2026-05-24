import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"

export function ConfirmPanel() {
  const planId = usePlanStore((s) => s.planId)
  const slots = usePlanStore((s) => s.slots)
  const awaitingConfirm = useAgentStore((s) => s.awaitingConfirm)
  const setAwaitingConfirm = useAgentStore((s) => s.setAwaitingConfirm)
  const setPlan = usePlanStore((s) => s.setPlan)
  if (!awaitingConfirm) return null

  const lockedSlots = slots.filter((_, i) => i < 1) // simplified: first slot is "locked"
  const unlockedSlots = slots.slice(1)

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
    <div className="mx-4 mb-3 p-3 rounded-lg bg-zinc-800 border border-zinc-700 space-y-3">
      <p className="text-xs text-zinc-300">确认这个计划吗？</p>

      {/* Slot status summary */}
      {slots.length > 0 && (
        <div className="space-y-1">
          {lockedSlots.length > 0 && (
            <div className="text-[10px] text-zinc-500">
              <span className="text-emerald-400">◆ Locked:</span>{" "}
              {lockedSlots.map((s) => s.poi.name).join(", ")}
            </div>
          )}
          {unlockedSlots.length > 0 && (
            <div className="text-[10px] text-zinc-500">
              <span className="text-amber-400">◇ Editable:</span>{" "}
              {unlockedSlots.map((s) => s.poi.name).join(", ")}
            </div>
          )}
        </div>
      )}

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
