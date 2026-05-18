import { usePlanStore } from "../../stores/planStore"

export function MapView() {
  const slots = usePlanStore((s) => s.slots)

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      <div className="px-4 py-3 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100">地图</h2>
      </div>
      <div className="flex-1 flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-900 to-zinc-950" />

        {slots.length === 0 && (
          <p className="relative text-sm text-zinc-600">输入目的地后显示地图</p>
        )}

        {slots.length > 0 && (
          <div className="relative w-full h-full p-4 space-y-3 overflow-auto">
            {slots.map((slot, i) => (
              <div
                key={slot.sequence}
                className="flex items-center gap-3 p-3 rounded-lg bg-zinc-800/50 border border-zinc-700/50"
              >
                <div className="w-8 h-8 rounded-full bg-rose-900/40 flex items-center justify-center text-xs text-rose-300 shrink-0">
                  {i + 1}
                </div>
                <div className="min-w-0">
                  <div className="text-sm text-zinc-200 truncate">{slot.poi.name}</div>
                  <div className="text-xs text-zinc-500">
                    {slot.poi.city} · {slot.poi.type}
                  </div>
                </div>
                <div className="text-xs text-zinc-600 shrink-0">
                  {slot.poi.rating} ★
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
