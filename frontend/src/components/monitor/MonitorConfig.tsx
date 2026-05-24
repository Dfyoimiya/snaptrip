import { useAlertStore } from "../../stores/alertStore"

export function MonitorConfig() {
  const monitorPlan = useAlertStore((s) => s.monitorPlan)

  if (!monitorPlan) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-xs font-semibold text-zinc-300 mb-3">Monitor Config</h3>
        <p className="text-xs text-zinc-600">Waiting for monitor plan...</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-xs font-semibold text-zinc-300 mb-3">Monitor Config</h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-zinc-500">Poll Interval</span>
          <span className="text-zinc-300 font-mono">{monitorPlan.poll_interval_s}s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Routes Tracked</span>
          <span className="text-zinc-300 font-mono">{monitorPlan.routes_to_track.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Queues Tracked</span>
          <span className="text-zinc-300 font-mono">{monitorPlan.queues_to_track.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Bookings Tracked</span>
          <span className="text-zinc-300 font-mono">{monitorPlan.bookings_to_track.length}</span>
        </div>
        {monitorPlan.deadline && (
          <div className="flex justify-between">
            <span className="text-zinc-500">Deadline</span>
            <span className="text-zinc-300 font-mono text-[10px]">
              {new Date(monitorPlan.deadline).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
