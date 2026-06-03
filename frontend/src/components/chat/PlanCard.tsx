import { useState, useEffect, useRef } from "react"
import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"
import type { PlanPreview } from "../../stores/chatStore"
import {
  Banknote, Pencil, Check, X, Loader2, AlertCircle,
  Utensils, MapPin, Coffee, Clock,
} from "lucide-react"

interface Props {
  plan: PlanPreview
}

/** Icon per action type */
function actionIcon(action?: string) {
  switch (action) {
    case "吃饭": case "午餐": case "晚餐": case "dining":
      return <Utensils size={11} className="text-orange-500" />
    case "喝咖啡": case "coffee": case "茶歇":
      return <Coffee size={11} className="text-amber-600" />
    default:
      return <MapPin size={11} className="text-blue-500" />
  }
}

export function PlanCard({ plan }: Props) {
  const planId = usePlanStore((s) => s.planId)
  const interruptPayload = useAgentStore((s) => s.interruptPayload)
  const setPlan = usePlanStore((s) => s.setPlan)
  const [editing, setEditing] = useState(false)
  const [editNote, setEditNote] = useState("")
  const [responding, setResponding] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState(false)

  // Only show action buttons when this card's plan is the active interrupt
  const isActive = interruptPayload?.type === "plan_confirm"

  // Reset submission state when plan data changes
  const planRef = useRef(plan)
  useEffect(() => {
    if (plan !== planRef.current) {
      setSubmitted(false)
      setError(false)
      setEditing(false)
      setEditNote("")
      planRef.current = plan
    }
  }, [plan])

  async function handleDecision(decision: string) {
    if (responding || submitted) return
    setResponding(true)
    setError(false)

    try {
      const extra = decision === "modified" ? { modification_instructions: editNote } : {}
      const resp = await confirmPlan(planId, { decision, ...extra })
      if (resp.code === 0 && resp.data) {
        setPlan(resp.data)
      }
      setSubmitted(true)
    } catch {
      setError(true)
    } finally {
      setResponding(false)
    }
  }

  return (
    <div className="bg-white border border-stone-200 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-stone-100 bg-stone-50/50 flex items-center gap-2">
        <MapPin size={14} className="text-emerald-500" />
        <span className="text-xs font-medium text-stone-500">行程方案</span>
      </div>

      {/* Plan details */}
      <div className="px-4 py-3 space-y-3">
        {plan.summary && (
          <p className="text-xs text-stone-500 leading-relaxed">{plan.summary}</p>
        )}

        {/* Total cost + time */}
        <div className="flex items-center gap-3 text-xs">
          {plan.total_cost != null && (
            <div className="flex items-center gap-1.5 text-stone-600">
              <Banknote size={13} className="text-emerald-500 shrink-0" />
              <span className="font-medium">¥{plan.total_cost}</span>
              <span className="text-stone-400">预估总费用</span>
            </div>
          )}
        </div>

        {/* Slots / Timeline */}
        {plan.slots && plan.slots.length > 0 && (
          <div className="border-t border-stone-100 pt-3 space-y-0">
            {plan.slots.map((s, i) => (
              <div key={i} className="flex gap-3">
                {/* Time column */}
                <div className="text-[10px] text-stone-400 w-14 shrink-0 text-right pt-0.5 leading-tight">
                  {(s.time_start || s.time_end) ? (
                    <>
                      <div>{s.time_start ?? "—"}</div>
                      <div className="text-stone-300">↓</div>
                      <div>{s.time_end ?? "—"}</div>
                    </>
                  ) : (
                    <span>时段{i + 1}</span>
                  )}
                </div>

                {/* Connector line + dot */}
                <div className="flex flex-col items-center shrink-0">
                  <div className={`
                    w-2 h-2 rounded-full border-2 shrink-0 mt-1
                    ${i === 0 ? "border-emerald-400 bg-emerald-100" : "border-stone-300 bg-white"}
                  `} />
                  {i < plan.slots!.length - 1 && (
                    <div className="w-px flex-1 bg-stone-200 min-h-[1.5rem]" />
                  )}
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0 pb-2.5">
                  <div className="flex items-center gap-1.5">
                    {actionIcon(s.action)}
                    {s.action && (
                      <span className="text-[10px] font-medium text-stone-400 bg-stone-100 px-1.5 py-0.5 rounded">
                        {s.action}
                      </span>
                    )}
                    {s.place && (
                      <span className="text-xs text-stone-700 font-medium truncate">{s.place}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {s.estimated_cost != null && s.estimated_cost > 0 && (
                      <span className="text-[10px] text-stone-400">¥{s.estimated_cost}</span>
                    )}
                    {s.note && (
                      <span className="text-[10px] text-stone-400 truncate">{s.note}</span>
                    )}
                    {(s.time_start || s.time_end) && (
                      <span className="text-[10px] text-stone-300 flex items-center gap-0.5">
                        <Clock size={10} />
                        {[s.time_start, s.time_end].filter(Boolean).join(" - ")}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Editing note */}
      {editing && !submitted && (
        <div className="px-4 pb-2">
          <textarea
            value={editNote}
            onChange={(e) => setEditNote(e.target.value)}
            placeholder="你想怎么调整？比如换一个餐厅、改预算…"
            rows={2}
            className="w-full text-xs border border-amber-200 rounded-lg px-3 py-2 resize-none outline-none focus:border-amber-300 bg-amber-50/30 placeholder:text-stone-400"
          />
        </div>
      )}

      {/* Actions / Status footer */}
      <div className="px-4 py-3 border-t border-stone-100 bg-stone-50/30">
        {submitted ? (
          <div className="flex items-center gap-2 text-xs text-emerald-700">
            <Check size={14} className="text-emerald-600" />
            已提交
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-xs text-red-600">
            <AlertCircle size={14} className="text-red-500" />
            提交失败，请重试
          </div>
        ) : !isActive ? (
          <span className="text-xs text-stone-400">历史方案</span>
        ) : !editing ? (
          <div className="grid grid-cols-3 gap-2">
            {/* Confirm card */}
            <button
              onClick={() => handleDecision("confirmed")}
              disabled={responding}
              className="flex flex-col items-center gap-1 px-3 py-2.5 bg-emerald-50 border border-emerald-200 rounded-xl
                         hover:bg-emerald-100 hover:border-emerald-300 hover:-translate-y-0.5
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {responding ? (
                <Loader2 size={16} className="animate-spin text-emerald-600" />
              ) : (
                <Check size={16} className="text-emerald-600" />
              )}
              <span className="text-xs font-medium text-emerald-700">确认</span>
              <span className="text-[10px] text-emerald-500">开始预订</span>
            </button>

            {/* Modify card */}
            <button
              onClick={() => setEditing(true)}
              disabled={responding}
              className="flex flex-col items-center gap-1 px-3 py-2.5 bg-amber-50 border border-amber-200 rounded-xl
                         hover:bg-amber-100 hover:border-amber-300 hover:-translate-y-0.5
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              <Pencil size={16} className="text-amber-600" />
              <span className="text-xs font-medium text-amber-700">修改</span>
              <span className="text-[10px] text-amber-500">调整细节</span>
            </button>

            {/* Reject card */}
            <button
              onClick={() => handleDecision("rejected")}
              disabled={responding}
              className="flex flex-col items-center gap-1 px-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl
                         hover:bg-stone-100 hover:border-stone-300 hover:-translate-y-0.5
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              <X size={16} className="text-stone-400" />
              <span className="text-xs font-medium text-stone-500">换一个</span>
              <span className="text-[10px] text-stone-400">生成新方案</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleDecision("modified")}
              disabled={responding || !editNote.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-amber-500 text-white rounded-lg
                         hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {responding ? <Loader2 size={13} className="animate-spin" /> : null}
              发送修改建议
            </button>
            <button
              onClick={() => {
                setEditing(false)
                setEditNote("")
              }}
              disabled={responding}
              className="px-3 py-1.5 text-xs text-stone-500 hover:text-stone-700 transition-colors"
            >
              取消
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
