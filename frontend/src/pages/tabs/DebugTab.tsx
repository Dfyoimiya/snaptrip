import { NodeStatusBar } from "../../components/debug/NodeStatusBar"
import { EventLog } from "../../components/debug/EventLog"

export function DebugTab() {
  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="px-4 py-2 border-b border-zinc-800 shrink-0">
        <h2 className="text-sm font-semibold text-zinc-100">Debug Console</h2>
      </div>
      <NodeStatusBar />
      <div className="flex-1 min-h-0">
        <EventLog />
      </div>
    </div>
  )
}
