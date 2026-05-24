import { useAgentStore } from "../../stores/agentStore"
import { clsx } from "clsx"

const STATUS_CLASS: Record<string, string> = {
  success: "text-emerald-400",
  failure: "text-red-400",
  timeout: "text-amber-400",
  skipped: "text-zinc-600 line-through",
}

export function ExecutionTable() {
  const executionState = useAgentStore((s) => s.executionState)
  const records = executionState?.tool_records ?? []

  if (records.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-zinc-600 p-4">
        No execution records yet
      </div>
    )
  }

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-zinc-500 border-b border-zinc-800 sticky top-0 bg-zinc-950">
          <th className="text-left px-4 py-2 font-medium">Slot</th>
          <th className="text-left px-4 py-2 font-medium">Tool</th>
          <th className="text-left px-4 py-2 font-medium">Layer</th>
          <th className="text-left px-4 py-2 font-medium">Status</th>
          <th className="text-left px-4 py-2 font-medium">Latency</th>
          <th className="text-left px-4 py-2 font-medium">Booking ID</th>
          <th className="text-left px-4 py-2 font-medium">Error</th>
        </tr>
      </thead>
      <tbody>
        {records.map((r) => (
          <tr key={r.invocation_id} className="border-b border-zinc-800/50 hover:bg-zinc-900/50">
            <td className="px-4 py-2 text-zinc-400">{r.slot_index}</td>
            <td className="px-4 py-2 text-zinc-300 font-mono">{r.tool_name}</td>
            <td className="px-4 py-2 text-zinc-500">L{r.layer}</td>
            <td className={clsx("px-4 py-2", STATUS_CLASS[r.status])}>{r.status}</td>
            <td className="px-4 py-2 text-zinc-500">{r.latency_ms}ms</td>
            <td className="px-4 py-2 text-zinc-500 font-mono">
              {r.booking_id ? r.booking_id.slice(0, 8) + "..." : "—"}
            </td>
            <td className="px-4 py-2 text-red-400/70 max-w-[200px] truncate">
              {r.error_message ?? "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
