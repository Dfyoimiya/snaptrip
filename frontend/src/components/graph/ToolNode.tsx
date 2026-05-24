import { Handle, Position } from "@xyflow/react"
import { clsx } from "clsx"
import type { ToolNodeData } from "../../types/agent"

const STATUS_COLOR: Record<string, string> = {
  pending: "border-zinc-600 bg-zinc-900 text-zinc-500",
  running: "border-amber-500 bg-amber-950/30 text-amber-300",
  success: "border-emerald-500 bg-emerald-950/30 text-emerald-300",
  failure: "border-red-500 bg-red-950/30 text-red-300",
  skipped: "border-zinc-500 bg-zinc-900/50 text-zinc-600 line-through",
}

export function ToolNode({ data }: { data: ToolNodeData }) {
  return (
    <div
      className={clsx(
        "px-2.5 py-1.5 rounded-md border min-w-[120px] text-xs transition-all duration-300",
        STATUS_COLOR[data.status],
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-zinc-500" />
      <div className="flex items-center gap-1">
        <span className="font-medium truncate">{data.human_readable_name}</span>
        {data.physical_impact && (
          <span className="text-[9px] text-rose-400" title="Physical impact">!</span>
        )}
      </div>
      <div className="text-[10px] opacity-50 mt-0.5">
        {data.name} · L{data.layer}
        {data.latency_ms != null && ` · ${data.latency_ms}ms`}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-zinc-500" />
    </div>
  )
}
