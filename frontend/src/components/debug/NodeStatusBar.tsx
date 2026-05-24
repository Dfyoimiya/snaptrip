import { useAgentStore } from "../../stores/agentStore"
import { clsx } from "clsx"

const STATUS_BAR_COLOR: Record<string, string> = {
  idle: "bg-zinc-700",
  running: "bg-amber-500 animate-pulse",
  done: "bg-emerald-500",
  error: "bg-red-500",
}

export function NodeStatusBar() {
  const nodes = useAgentStore((s) => s.nodes)

  return (
    <div className="px-4 py-2 border-b border-zinc-800 shrink-0">
      <div className="flex items-center gap-1.5">
        {nodes.map((n) => (
          <div key={n.id} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={clsx("w-full h-1.5 rounded-full transition-colors duration-300", STATUS_BAR_COLOR[n.status])}
            />
            <span className="text-[9px] text-zinc-600 truncate max-w-[60px] text-center leading-tight">
              {n.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
