import { WorkflowGraph } from "../../components/graph/WorkflowGraph"
import { GraphLegend } from "../../components/graph/GraphLegend"
import { useAgentStore } from "../../stores/agentStore"

export function GraphTab() {
  const isRunning = useAgentStore((s) => s.isRunning)
  const mode = useAgentStore((s) => s.mode)

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between shrink-0">
        <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <span>Agent Pipeline</span>
          {isRunning && (
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          )}
        </h2>
        <span className="text-xs text-zinc-500">
          {mode === "multi" ? "10 nodes (multi-agent)" : "6 nodes (single-agent)"}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <WorkflowGraph />
      </div>
      <div className="px-4 py-2 border-t border-zinc-800 shrink-0">
        <GraphLegend />
      </div>
    </div>
  )
}
