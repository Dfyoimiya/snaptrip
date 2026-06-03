import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"

export function ConfirmPanel() {
  const planId = usePlanStore((s) => s.planId)
  const interruptPayload = useAgentStore((s) => s.interruptPayload)
  const setInterruptPayload = useAgentStore((s) => s.setInterruptPayload)
  const setPlan = usePlanStore((s) => s.setPlan)

  // Only show for plan_confirm interrupts
  if (!interruptPayload || interruptPayload.type !== "plan_confirm") return null

  const plan = interruptPayload.plan

  async function handleConfirm(decision: string) {
    setInterruptPayload(null)
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
      <p className="text-xs text-zinc-300">
        {interruptPayload.message || "确认这个计划吗？"}
      </p>

      {/* Plan summary from interrupt payload */}
      {plan && (
        <div className="space-y-1.5 text-[10px] text-zinc-400">
          {plan.summary && (
            <div className="text-zinc-300 mb-1">{plan.summary}</div>
          )}
          {plan.total_cost != null && (
            <div>
              <span className="text-zinc-500">总费用:</span>{" "}
              <span className="text-emerald-400">¥{plan.total_cost}</span>
            </div>
          )}
        </div>
      )}

      {/* Show slots if present — structured timeline form */}
      {plan?.slots && plan.slots.length > 0 && (
        <div className="space-y-1.5 border-t border-zinc-700 pt-2">
          {plan.slots.map((s, i) => (
            <div key={i} className="flex gap-2 text-[10px]">
              <span className="text-zinc-500 w-16 shrink-0 text-right">
                {(s.time_start || s.time_end)
                  ? `${s.time_start ?? "—"}~${s.time_end ?? "—"}`
                  : `时段 ${i + 1}`}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  {s.action && (
                    <span className="text-[9px] bg-zinc-600 text-zinc-300 px-1 rounded">{s.action}</span>
                  )}
                  {s.place && (
                    <span className="text-zinc-300 truncate">{s.place}</span>
                  )}
                </div>
                <div className="flex gap-2 mt-0.5">
                  {s.estimated_cost != null && s.estimated_cost > 0 && (
                    <span className="text-zinc-500">¥{s.estimated_cost}</span>
                  )}
                  {s.note && (
                    <span className="text-zinc-500 truncate">{s.note}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 py-1.5 text-xs rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
          onClick={() => handleConfirm("confirmed")}
        >
          确认
        </button>
        <button
          className="flex-1 py-1.5 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
          onClick={() => handleConfirm("modified")}
        >
          修改
        </button>
        <button
          className="flex-1 py-1.5 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
          onClick={() => handleConfirm("rejected")}
        >
          拒绝
        </button>
      </div>
    </div>
  )
}
