import { clsx } from "clsx"

export type TabId = "plan" | "graph" | "monitor" | "execution" | "debug"

const TABS: { id: TabId; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "graph", label: "Graph" },
  { id: "monitor", label: "Monitor" },
  { id: "execution", label: "Execution" },
  { id: "debug", label: "Debug" },
]

interface Props {
  active: TabId
  onSelect: (tab: TabId) => void
}

export function DashboardTabs({ active, onSelect }: Props) {
  return (
    <div className="flex gap-0 border-b border-zinc-800 shrink-0">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className={clsx(
            "px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px",
            active === t.id
              ? "text-rose-400 border-rose-400"
              : "text-zinc-500 border-transparent hover:text-zinc-300",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}
