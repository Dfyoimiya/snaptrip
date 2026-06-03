import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"

export function QuestionPanel() {
  const planId = usePlanStore((s) => s.planId)
  const interruptPayload = useAgentStore((s) => s.interruptPayload)
  const setInterruptPayload = useAgentStore((s) => s.setInterruptPayload)

  // Only show for question interrupts
  if (!interruptPayload || interruptPayload.type !== "question") return null

  async function handleReply(answer: string) {
    setInterruptPayload(null)
    try {
      await confirmPlan(planId, { decision: answer })
    } catch {
      // ignore
    }
  }

  return (
    <div className="mx-4 mb-3 p-3 rounded-lg bg-zinc-800 border border-zinc-700 space-y-3">
      <p className="text-xs text-zinc-300">
        {interruptPayload.message || "需要你的回应"}
      </p>

      {interruptPayload.options.length > 0 && (
        <div className="space-y-1.5">
          {interruptPayload.options.map((opt, i) => (
            <button
              key={i}
              className="w-full text-left py-1.5 px-2 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
              onClick={() => handleReply(opt.value || opt.label)}
            >
              {opt.label}
              {opt.description && (
                <span className="block text-[10px] text-zinc-500 mt-0.5">{opt.description}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
