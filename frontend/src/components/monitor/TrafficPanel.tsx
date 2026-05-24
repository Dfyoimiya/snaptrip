import { useAlertStore } from "../../stores/alertStore"

export function TrafficPanel() {
  const ctx = useAlertStore((s) => s.realtimeContext)
  const t = ctx?.traffic_index

  if (!t) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-xs font-semibold text-zinc-300 mb-3">Traffic Index</h3>
        <p className="text-xs text-zinc-600">Waiting for real-time context...</p>
      </div>
    )
  }

  const pct = (t.overall * 100).toFixed(0)
  const color = t.overall < 0.3 ? "text-emerald-400" : t.overall < 0.6 ? "text-amber-400" : "text-red-400"
  const barColor = t.overall < 0.3 ? "#10b981" : t.overall < 0.6 ? "#f59e0b" : "#ef4444"

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-xs font-semibold text-zinc-300 mb-3">Traffic Index</h3>
      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold font-mono ${color}`}>{pct}%</span>
        <span className="text-xs text-zinc-500">
          {t.overall < 0.3 ? "Clear" : t.overall < 0.6 ? "Moderate" : "Congested"}
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mt-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
      {Object.keys(t.by_corridor).length > 0 && (
        <div className="mt-3 space-y-1">
          <div className="text-[10px] text-zinc-600 mb-1">Corridors</div>
          {Object.entries(t.by_corridor).slice(0, 5).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-xs">
              <span className="text-zinc-500 font-mono text-[10px] truncate max-w-[180px]">{k}</span>
              <span className={`font-mono ${v < 0.3 ? "text-emerald-400" : v < 0.6 ? "text-amber-400" : "text-red-400"}`}>
                {(v * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
