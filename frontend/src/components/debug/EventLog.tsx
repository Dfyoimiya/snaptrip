import { useMemo, useState } from "react"
import { useAgentStore } from "../../stores/agentStore"

export function EventLog() {
  const logs = useAgentStore((s) => s.logs)
  const [filter, setFilter] = useState("")

  const filtered = useMemo(() => {
    if (!filter.trim()) return logs
    const q = filter.toLowerCase()
    return logs.filter((l) => l.toLowerCase().includes(q))
  }, [logs, filter])

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-zinc-800 shrink-0">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter events..."
          className="w-full bg-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 rounded px-2 py-1 outline-none border border-zinc-700 focus:border-rose-500/50"
        />
      </div>
      <div className="flex-1 overflow-auto p-4 font-mono text-xs text-zinc-500 space-y-1">
        {filtered.length === 0 && (
          <span className="text-zinc-700">
            {logs.length === 0 ? "Waiting for events..." : "No matching events"}
          </span>
        )}
        {filtered.map((l, i) => {
          try {
            const obj = JSON.parse(l)
            const evt = obj.event ?? "unknown"
            const time = obj.timestamp ? new Date(obj.timestamp).toLocaleTimeString() : ""
            return (
              <div key={i} className="break-all leading-relaxed">
                <span className="text-rose-400">{evt}</span>
                {time && <span className="text-zinc-600 ml-2">{time}</span>}
                <span className="text-zinc-700 ml-2">
                  {JSON.stringify(obj, null, 0).slice(0, 150)}
                </span>
              </div>
            )
          } catch {
            return (
              <div key={i} className="break-all text-zinc-700">
                {l}
              </div>
            )
          }
        })}
      </div>
    </div>
  )
}
