import { useAlertStore } from "../../stores/alertStore"
import { clsx } from "clsx"
import type { AlertSeverity } from "../../types/agent"

const SEVERITY_COLOR: Record<AlertSeverity, string> = {
  info: "border-blue-500/30 bg-blue-950/20",
  warning: "border-amber-500/30 bg-amber-950/20",
  critical: "border-red-500/30 bg-red-950/20",
}

const SEVERITY_DOT: Record<AlertSeverity, string> = {
  info: "bg-blue-400",
  warning: "bg-amber-400",
  critical: "bg-red-400",
}

const ACTION_LABEL: Record<string, string> = {
  no_op: "No action",
  partial_replan: "Partial replan",
  full_replan: "Full replan",
  cancel: "Cancel",
}

export function AlertFeed() {
  const alerts = useAlertStore((s) => s.alerts)

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-zinc-300">Alerts</h3>
        <span className="text-[10px] text-zinc-600">{alerts.length} total</span>
      </div>
      <div className="max-h-80 overflow-auto">
        {alerts.length === 0 ? (
          <p className="text-xs text-zinc-600 p-4">No alerts yet. Alerts appear when monitor engine detects anomalies.</p>
        ) : (
          alerts.map((a, i) => (
            <div
              key={i}
              className={clsx("px-4 py-2.5 border-b border-zinc-800/50 last:border-0", SEVERITY_COLOR[a.severity])}
            >
              <div className="flex items-center gap-2">
                <span className={clsx("inline-block w-2 h-2 rounded-full", SEVERITY_DOT[a.severity])} />
                <span className="text-xs font-medium text-zinc-200">{a.alert_type}</span>
                <span className={clsx(
                  "text-[10px] px-1.5 py-0.5 rounded",
                  a.severity === "critical" ? "bg-red-900/50 text-red-300" :
                  a.severity === "warning" ? "bg-amber-900/50 text-amber-300" :
                  "bg-blue-900/50 text-blue-300",
                )}>
                  {a.severity}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-1">{a.message}</p>
              <div className="flex items-center gap-3 mt-1.5 text-[10px] text-zinc-500">
                <span>Slots: [{a.slot_indices.join(", ")}]</span>
                <span>Action: {ACTION_LABEL[a.suggested_action] ?? a.suggested_action}</span>
                {a.timestamp && <span className="text-zinc-600">{new Date(a.timestamp).toLocaleTimeString()}</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
