import { useAlertStore } from "../../stores/alertStore"

export function PeakPanel() {
  const ctx = useAlertStore((s) => s.realtimeContext)
  const p = ctx?.peak_calendar

  if (!p) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-xs font-semibold text-zinc-300 mb-3">Peak Hours</h3>
        <p className="text-xs text-zinc-600">Waiting for real-time context...</p>
      </div>
    )
  }

  const maxMult = Math.max(1, ...Object.values(p.hourly_multipliers))

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-xs font-semibold text-zinc-300 mb-3">Peak Hours</h3>

      {/* Heatmap bars */}
      <div className="flex items-end gap-0.5 h-16 mb-3">
        {Array.from({ length: 24 }, (_, h) => {
          const mult = p.hourly_multipliers[h] ?? 0
          const heightPct = maxMult > 0 ? (mult / maxMult) * 100 : 0
          const isPeak = mult > 1
          return (
            <div key={h} className="flex-1 flex flex-col items-center gap-0.5">
              <div
                className="w-full rounded-t transition-all duration-300"
                style={{
                  height: `${Math.max(heightPct, 2)}%`,
                  backgroundColor: isPeak ? "#ef4444" : mult > 0.5 ? "#f59e0b" : "#3f3f46",
                }}
              />
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-[10px] text-zinc-600 px-0.5">
        <span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>23h</span>
      </div>

      {/* Special Events */}
      {p.special_events.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] text-zinc-600 mb-1">Special Events</div>
          {p.special_events.map((ev, i) => (
            <span key={i} className="inline-block text-[10px] bg-rose-900/30 text-rose-300 px-1.5 py-0.5 rounded mr-1 mb-1">
              {ev}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
