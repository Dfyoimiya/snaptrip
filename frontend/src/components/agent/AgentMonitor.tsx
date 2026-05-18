import { useAgentStore } from "../../stores/agentStore"
import type { AgentNode } from "../../types/agent"

function statusColor(s: AgentNode["status"]) {
  switch (s) {
    case "running":
      return "text-amber-400"
    case "done":
      return "text-emerald-400"
    case "error":
      return "text-red-400"
    default:
      return "text-zinc-600"
  }
}

function statusIcon(s: AgentNode["status"]) {
  if (s === "running") return "⟳"
  if (s === "done") return "✓"
  return "○"
}

function PipelineNode({ node }: { node: AgentNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs w-4 ${statusColor(node.status)}`}>
        {statusIcon(node.status)}
      </span>
      <span className={`text-xs ${node.status === "idle" ? "text-zinc-600" : "text-zinc-300"}`}>
        {node.label}
      </span>
    </div>
  )
}

export function AgentMonitor() {
  const nodes = useAgentStore((s) => s.nodes)
  const logs = useAgentStore((s) => s.logs)
  const isRunning = useAgentStore((s) => s.isRunning)

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      <div className="px-4 py-3 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <span>Agent 大脑</span>
          {isRunning && (
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          )}
        </h2>
      </div>

      <div className="px-4 py-3 space-y-2 border-b border-zinc-800">
        {nodes.map((n) => (
          <PipelineNode key={n.id} node={n} />
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="font-mono text-xs text-zinc-500 space-y-1">
          {logs.length === 0 && (
            <span className="text-zinc-700">等待 Agent 启动...</span>
          )}
          {logs.map((l, i) => (
            <div key={i} className="break-all">
              {l}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
