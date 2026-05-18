import type { PlanSlot } from "../../types/plan"

function timeStr(iso: string) {
  return new Date(iso).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function SlotDetail({ slot }: { slot: PlanSlot }) {
  const start = timeStr(slot.time_range.start)
  const end = timeStr(slot.time_range.end)

  const actionLabel: Record<string, string> = {
    arrive: "前往",
    book_table: "订座",
    book_ticket: "购票",
    order: "下单",
  }

  return (
    <div className="flex items-start gap-3 py-3 border-b border-zinc-800 last:border-0">
      <div className="text-xs text-rose-400 w-14 shrink-0 pt-0.5">
        {start}
        <br />
        {end}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-zinc-100">{slot.poi.name}</div>
        <div className="text-xs text-zinc-500 mt-0.5">
          {actionLabel[slot.action] ?? slot.action}
          {" · "}
          {slot.poi.type === "restaurant"
            ? "餐饮"
            : slot.poi.type === "cafe"
              ? "咖啡"
              : slot.poi.type === "attraction"
                ? "景点"
                : "活动"}
        </div>
      </div>
      <div className="text-sm text-zinc-300 shrink-0">¥{slot.estimated_cost}</div>
    </div>
  )
}

export function PlanTimeline({ slots }: { slots: PlanSlot[] }) {
  if (slots.length === 0) {
    return <p className="text-sm text-zinc-500 px-4">暂无活动安排</p>
  }
  return (
    <div className="px-4">
      {slots.map((s) => (
        <SlotDetail key={s.sequence} slot={s} />
      ))}
    </div>
  )
}

export function PlanCard() {
  // reads from store
  return null
}
