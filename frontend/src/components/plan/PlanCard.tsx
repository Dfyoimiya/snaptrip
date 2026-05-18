import { usePlanStore } from "../../stores/planStore"
import { PlanTimeline } from "./PlanTimeline"

export function PlanCard() {
  const slots = usePlanStore((s) => s.slots)
  const totalCost = usePlanStore((s) => s.totalCost)
  const totalTimeMin = usePlanStore((s) => s.totalTimeMin)
  const shareCard = usePlanStore((s) => s.shareCard)

  return (
    <div className="flex flex-col h-full bg-zinc-900">
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-100">计划详情</h2>
        {slots.length > 0 && (
          <span className="text-xs text-zinc-500">
            {totalTimeMin} 分钟 · ¥{totalCost}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        <PlanTimeline slots={slots} />
      </div>

      {shareCard && (
        <div className="px-4 py-3 border-t border-zinc-800">
          <p className="text-xs text-zinc-400">{shareCard.message}</p>
        </div>
      )}
    </div>
  )
}
