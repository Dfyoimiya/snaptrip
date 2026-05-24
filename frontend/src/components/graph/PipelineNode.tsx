import { Handle, Position } from "@xyflow/react"
import { clsx } from "clsx"
import type { PipelineNodeData } from "../../types/agent"

const STATUS_COLOR: Record<string, string> = {
  idle: "border-zinc-600 bg-zinc-900 text-zinc-500",
  running: "border-amber-500 bg-amber-950/30 text-amber-300 shadow-amber-500/20 shadow-lg",
  done: "border-emerald-500 bg-emerald-950/30 text-emerald-300",
  error: "border-red-500 bg-red-950/30 text-red-300",
}

const TYPE_ICON: Record<string, string> = {
  engine: "⚙",
  checkpoint: "◆",
  monitor: "◇",
}

export function PipelineNode({ data }: { data: PipelineNodeData }) {
  const isRunning = data.status === "running"

  return (
    <div
      className={clsx(
        "px-3 py-2 rounded-lg border-2 min-w-[140px] transition-all duration-300",
        STATUS_COLOR[data.status],
        isRunning && "animate-pulse",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-zinc-500" />
      <div className="flex items-center gap-1.5">
        <span className="text-xs">{TYPE_ICON[data.type]}</span>
        <span className="text-xs font-medium">{data.label}</span>
      </div>
      <div className="text-[10px] mt-0.5 opacity-60">
        Layer {data.layer} · {data.type}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-zinc-500" />
    </div>
  )
}
