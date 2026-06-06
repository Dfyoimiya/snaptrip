import { useEffect, useRef } from "react"
import { sseUrl } from "../api/plan"
import { useAgentStore } from "../stores/agentStore"
import { useChatStore } from "../stores/chatStore"
import { usePlanStore } from "../stores/planStore"
import type { InterruptPayload, OptionItem } from "../types/agent"

/**
 * Normalize options from backend (handles both legacy string[] and new OptionItem[]).
 */
function normalizeOptions(raw: unknown): OptionItem[] {
  if (!Array.isArray(raw)) return []
  return raw.map((item: unknown): OptionItem => {
    if (typeof item === "string") {
      return { label: item, value: item }
    }
    if (typeof item === "object" && item !== null) {
      const obj = item as Record<string, unknown>
      return {
        label: String(obj.label ?? obj.value ?? ""),
        value: String(obj.value ?? obj.label ?? ""),
        description: obj.description ? String(obj.description) : undefined,
      }
    }
    return { label: String(item), value: String(item) }
  })
}

/**
 * Safely parse SSE event data.
 */
function parseSSEData<T>(data: string, eventName: string): T | null {
  try {
    return JSON.parse(data) as T
  } catch {
    console.error(`[SSE] ${eventName} parse error:`, data.slice(0, 200))
    return null
  }
}

export function usePlanSSE(planId: string | null) {
  const setRunning = useAgentStore((s) => s.setRunning)
  const setInterruptPayload = useAgentStore((s) => s.setInterruptPayload)
  const addMessage = useChatStore((s) => s.addMessage)
  const updateLastAssistant = useChatStore((s) => s.updateLastAssistant)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const attachPlanToLastAssistant = useChatStore((s) => s.attachPlanToLastAssistant)
  const setStatus = usePlanStore((s) => s.setStatus)

  const retriesRef = useRef(0)
  const MAX_RETRIES = 3

  useEffect(() => {
    if (!planId) return

    let es: EventSource | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      es = new EventSource(sseUrl(planId!))
      setRunning(true)

      es.onopen = () => {
        retriesRef.current = 0
      }

      // ── HITL: question ──
      es.addEventListener("question", (e: MessageEvent) => {
        const raw = parseSSEData<Record<string, unknown>>(e.data, "question")
        if (!raw) return

        const message = String(raw.message ?? "")
        const options = normalizeOptions(raw.options)

        console.log("[SSE] question:", { message: message.slice(0, 80), options: options.length })

        if (message) {
          updateLastAssistant(message)
        }
        setInterruptPayload({
          type: "question",
          message,
          options,
        } satisfies InterruptPayload)
      })

      // ── HITL: plan confirmation ──
      es.addEventListener("need_confirmation", (e: MessageEvent) => {
        const raw = parseSSEData<Record<string, unknown>>(e.data, "need_confirmation")
        if (!raw) return

        const message = String(raw.message ?? "")
        const planData = (raw.plan ?? null) as InterruptPayload["plan"]
        const options = normalizeOptions(raw.options)

        console.log("[SSE] need_confirmation:", { message: message.slice(0, 80), hasPlan: !!planData })

        if (message) {
          updateLastAssistant(message)
        }
        if (planData) {
          attachPlanToLastAssistant(planData)
        }
        setInterruptPayload({
          type: "plan_confirm",
          message,
          options,
          plan: planData,
        } satisfies InterruptPayload)
      })

      // ── HITL: booking confirmation ──
      es.addEventListener("confirm_booking", (e: MessageEvent) => {
        const raw = parseSSEData<Record<string, unknown>>(e.data, "confirm_booking")
        if (!raw) return

        const message = String(raw.message ?? "")
        const booking = (raw.booking ?? null) as InterruptPayload["booking"]
        const options = normalizeOptions(raw.options)

        console.log("[SSE] confirm_booking:", { message: message.slice(0, 80), hasBooking: !!booking })

        if (message) {
          updateLastAssistant(message)
        }
        setInterruptPayload({
          type: "booking_confirm",
          message,
          options: options.length > 0 ? options : [
            { label: "确认预订", value: "confirmed", description: "执行预订" },
            { label: "取消", value: "rejected", description: "放弃本次预订" },
          ],
          booking,
        } satisfies InterruptPayload)
      })

      // ── Progress events ──
      const progressEvents = [
        "intent", "intent_done",
        "planning", "planning_done",
        "searching_activities", "activities_found",
        "searching_restaurants", "restaurants_found",
        "validating", "validation_done",
        "scoring", "scoring_done",
        "composing", "itinerary_ready",
        "retrieval", "execution", "execution_done",
        "execution_failed", "notify", "notified",
        "context_loaded", "memory_loaded",
      ]
      for (const eventName of progressEvents) {
        es.addEventListener(eventName, () => {
          // Progress milestones — no UI update needed currently
        })
      }

      // ── Terminal event ──
      es.addEventListener("done", () => {
        setRunning(false)
        setStreaming(false)
        setStatus("done")
        setInterruptPayload(null)
      })

      es.onerror = () => {
        es?.close()
        setInterruptPayload(null)
        if (retriesRef.current < MAX_RETRIES) {
          retriesRef.current++
          const delay = Math.pow(2, retriesRef.current - 1) * 1000
          retryTimer = setTimeout(connect, delay)
        } else {
          setRunning(false)
          setStreaming(false)
          updateLastAssistant("抱歉，连接似乎出了点问题。请稍后再试。")
        }
      }
    }

    connect()

    return () => {
      es?.close()
      if (retryTimer) clearTimeout(retryTimer)
      setRunning(false)
      setStreaming(false)
    }
  }, [planId, setRunning, setInterruptPayload, updateLastAssistant, addMessage, setStreaming, attachPlanToLastAssistant, setStatus])
}
