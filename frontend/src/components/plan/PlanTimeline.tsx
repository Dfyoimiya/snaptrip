import type { PlanSlot } from "../../types/plan"

function timeStr(iso: string) {
  return new Date(iso).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  })
}

const ACTION_LABEL: Record<string, string> = {
  arrive: "前往",
  book_table: "订座",
  book_ticket: "购票",
  order: "下单",
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = (value * 100).toFixed(0)
  const color = value > 0.7 ? "#10b981" : value > 0.4 ? "#f59e0b" : "#ef4444"
  return (
    <div className="flex items-center gap-1.5 mt-1">
      <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] text-zinc-600 font-mono">{pct}%</span>
    </div>
  )
}

export function SlotDetail({ slot }: { slot: PlanSlot }) {
  const start = timeStr(slot.time_range.start)
  const end = timeStr(slot.time_range.end)

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
          {ACTION_LABEL[slot.action] ?? slot.action}
          {" · "}
          {slot.poi.type === "restaurant"
            ? "餐饮"
            : slot.poi.type === "cafe"
              ? "咖啡"
              : slot.poi.type === "attraction"
                ? "景点"
                : slot.poi.type === "activity"
                  ? "活动"
                  : slot.poi.type}
        </div>
        {slot.move_time_min > 0 && (
          <div className="text-[10px] text-zinc-600 mt-0.5">
            ← {slot.move_time_min}min travel
          </div>
        )}
        <ConfidenceBar value={slot.confidence} />
        {slot.rationale && slot.rationale.length > 0 && (
          <div className="mt-1 text-[10px] text-zinc-500">
            {slot.rationale.map((r, i) => (
              <span key={i} className="block leading-relaxed">{r}</span>
            ))}
          </div>
        )}
        {slot.alternatives && slot.alternatives.length > 0 && (
          <div className="mt-1.5 flex items-center gap-1 flex-wrap">
            <span className="text-[10px] text-zinc-600">Alt:</span>
            {slot.alternatives.slice(0, 3).map((a) => (
              <span
                key={a.poi_id}
                className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400"
              >
                {a.poi_id.slice(0, 8)} {a.prechecked ? "✓" : ""} {a.score.toFixed(1)}
              </span>
            ))}
            {slot.alternatives.length > 3 && (
              <span className="text-[10px] text-zinc-600">+{slot.alternatives.length - 3}</span>
            )}
          </div>
        )}
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
