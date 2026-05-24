export function GraphLegend() {
  const items = [
    { color: "bg-zinc-600", label: "Idle" },
    { color: "bg-amber-500", label: "Running", pulse: true },
    { color: "bg-emerald-500", label: "Done" },
    { color: "bg-red-500", label: "Error" },
  ]

  return (
    <div className="flex items-center gap-4 text-xs text-zinc-500">
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${item.color} ${item.pulse ? "animate-pulse" : ""}`}
          />
          {item.label}
        </span>
      ))}
      <span className="text-zinc-700">|</span>
      <span>⚙ Engine</span>
      <span>◆ Checkpoint</span>
      <span>◇ Monitor</span>
    </div>
  )
}
