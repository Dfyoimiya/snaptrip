import { ExecutionDAG } from "../../components/graph/ExecutionDAG"
import { ExecutionTable } from "../../components/execution/ExecutionTable"
import { useAgentStore } from "../../stores/agentStore"

export function ExecutionTab() {
  const executionState = useAgentStore((s) => s.executionState)

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between shrink-0">
        <h2 className="text-sm font-semibold text-zinc-100">
          Tool Execution DAG (17 tools, 4 layers)
        </h2>
        {executionState && (
          <span className="text-xs text-zinc-500">
            {executionState.tool_records.length} records · {executionState.total_elapsed_ms}ms ·{" "}
            <span className={
              executionState.status === "full_success" ? "text-emerald-400" :
              executionState.status === "partial_success" ? "text-amber-400" : "text-red-400"
            }>
              {executionState.status}
            </span>
          </span>
        )}
      </div>
      {/* Upper: DAG */}
      <div className="h-[55%] border-b border-zinc-800">
        <ExecutionDAG />
      </div>
      {/* Lower: Table */}
      <div className="flex-1 min-h-0 overflow-auto">
        <ExecutionTable />
      </div>
    </div>
  )
}
