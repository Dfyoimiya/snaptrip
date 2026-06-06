import { useState, useEffect, useRef } from "react"
import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"
import { HelpCircle, Check, AlertCircle, Loader2 } from "lucide-react"
import { OptionCard } from "./OptionCard"
import { MarkdownText } from "./MarkdownText"

export function QuestionCard() {
  const planId = usePlanStore((s) => s.planId)
  const interruptPayload = useAgentStore((s) => s.interruptPayload)
  const [submitting, setSubmitting] = useState(false)
  const [selectedValue, setSelectedValue] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState(false)

  // Reset submission state when a new question arrives
  const interruptKey =
    interruptPayload?.message + "|" + (interruptPayload?.options ?? [])
      .map((o) => o.value || o.label)
      .join(",")
  const prevKeyRef = useRef(interruptKey)
  useEffect(() => {
    if (interruptKey !== prevKeyRef.current) {
      setSubmitted(false)
      setError(false)
      setSelectedValue(null)
      prevKeyRef.current = interruptKey
    }
  }, [interruptKey])

  if (!interruptPayload || interruptPayload.type !== "question") return null

  const options = interruptPayload.options ?? []

  async function handleReply(value: string) {
    if (submitting || submitted) return
    setSelectedValue(value)
    setSubmitting(true)
    setError(false)

    try {
      await confirmPlan(planId, {
        decision: "confirmed",
        modification_instructions: value,
      })
      setSubmitted(true)
    } catch {
      setError(true)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white border border-stone-200 rounded-xl overflow-hidden shadow-sm animate-slide-up">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-stone-100 bg-stone-50/50 flex items-center gap-2">
        <HelpCircle size={14} className="text-amber-500" />
        <span className="text-xs font-medium text-stone-500">需要确认</span>
      </div>

      <div className="px-4 py-3">
        {/* Message with markdown rendering */}
        <div className="text-sm text-stone-700 leading-relaxed mb-3 prose-clean">
          <MarkdownText>{interruptPayload.message}</MarkdownText>
        </div>

        {/* Status: submitted */}
        {submitted ? (
          <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg">
            <Check size={14} className="text-emerald-600" />
            <span className="text-xs font-medium text-emerald-700">
              已选择: {selectedValue}
            </span>
          </div>
        ) : error ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle size={14} className="text-red-500" />
              <span className="text-xs text-red-600">提交失败，请重试</span>
            </div>
            {options.length > 0 && (
              <div className="space-y-2">
                {options.map((opt, i) => (
                  <OptionCard
                    key={i}
                    option={opt}
                    selected={selectedValue === (opt.value || opt.label)}
                    disabled={submitting}
                    loading={submitting && selectedValue === (opt.value || opt.label)}
                    onClick={() => handleReply(opt.value || opt.label)}
                  />
                ))}
              </div>
            )}
          </div>
        ) : options.length > 0 ? (
          <div className="space-y-2">
            {options.map((opt, i) => (
              <OptionCard
                key={i}
                option={opt}
                selected={selectedValue === (opt.value || opt.label)}
                disabled={submitting}
                loading={submitting && selectedValue === (opt.value || opt.label)}
                onClick={() => handleReply(opt.value || opt.label)}
              />
            ))}
          </div>
        ) : (
          /* No options — free text mode */
          <p className="text-xs text-stone-400 italic">
            等待 LLM 回复中...
          </p>
        )}
      </div>
    </div>
  )
}
