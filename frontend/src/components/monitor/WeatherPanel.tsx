import { useAlertStore } from "../../stores/alertStore"
import { Cloud, CloudRain, CloudSnow, Sun, CloudLightning } from "lucide-react"

const WEATHER_ICON: Record<string, typeof Sun> = {
  sunny: Sun,
  cloudy: Cloud,
  rainy: CloudRain,
  snowy: CloudSnow,
  stormy: CloudLightning,
}

const WEATHER_COLOR: Record<string, string> = {
  sunny: "text-amber-400",
  cloudy: "text-zinc-400",
  rainy: "text-blue-400",
  snowy: "text-blue-200",
  stormy: "text-purple-400",
}

export function WeatherPanel() {
  const ctx = useAlertStore((s) => s.realtimeContext)
  const w = ctx?.weather

  if (!w) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-xs font-semibold text-zinc-300 mb-3">Weather</h3>
        <p className="text-xs text-zinc-600">Waiting for real-time context...</p>
      </div>
    )
  }

  const Icon = WEATHER_ICON[w.condition] ?? Cloud

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-xs font-semibold text-zinc-300 mb-3">Weather</h3>
      <div className="flex items-center gap-3">
        <Icon size={28} className={WEATHER_COLOR[w.condition] ?? "text-zinc-400"} />
        <div>
          <div className="text-lg font-bold text-zinc-100">{w.temperature_c}°C</div>
          <div className="text-xs text-zinc-500 capitalize">{w.condition}</div>
        </div>
      </div>
      <div className="mt-3 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-500">Outdoor score</span>
          <span className={`font-mono ${w.outdoor_score > 0.5 ? "text-emerald-400" : w.outdoor_score > 0.3 ? "text-amber-400" : "text-red-400"}`}>
            {w.outdoor_score.toFixed(2)}
          </span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${(w.outdoor_score * 100).toFixed(0)}%`,
              backgroundColor: w.outdoor_score > 0.5 ? "#10b981" : w.outdoor_score > 0.3 ? "#f59e0b" : "#ef4444",
            }}
          />
        </div>
        <div className="text-[10px] text-zinc-600">
          Reported: {new Date(w.report_time).toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}
