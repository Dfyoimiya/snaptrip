import { useCallback, useState } from "react"
import { confirmPlan, createPlan } from "./api/plan"
import { Sidebar } from "./components/chat/Sidebar"
import { ChatView } from "./components/chat/ChatView"
import { ChatInput } from "./components/chat/ChatInput"
import { usePlanSSE } from "./hooks/usePlanSSE"
import { useGeolocation } from "./hooks/useGeolocation"
import { useChatStore } from "./stores/chatStore"
import { useAgentStore } from "./stores/agentStore"
import { usePlanStore } from "./stores/planStore"
import type { PlanCreateRequest } from "./types/plan"

export default function App() {
  const [loading, setLoading] = useState(false)
  const geo = useGeolocation()

  const planId = usePlanStore((s) => s.planId)
  const planReset = usePlanStore((s) => s.reset)
  const agentReset = useAgentStore((s) => s.reset)
  const chatReset = useChatStore((s) => s.reset)
  const addMessage = useChatStore((s) => s.addMessage)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const setRunning = useAgentStore((s) => s.setRunning)
  const setConversationMeta = useChatStore((s) => s.setConversationMeta)

  // SSE connects when we have a planId
  usePlanSSE(planId)

  const handleSend = useCallback(
    async (text: string) => {
      setLoading(true)

      // If an interrupt is active (question or plan confirm), reply to the
      // existing plan instead of creating a new one — preserves conversation
      // context and chain of thought.
      const interrupt = useAgentStore.getState().interruptPayload
      const currentPlanId = usePlanStore.getState().planId
      if (interrupt && currentPlanId) {
        addMessage({ role: "user", content: text })
        addMessage({ role: "assistant", content: "" })
        setRunning(true)
        setStreaming(true)
        // SSE will clear interruptPayload on next event; don't clear here

        try {
          await confirmPlan(currentPlanId, {
            decision: "confirmed",
            modification_instructions: text,
          })
          // SSE stream resumes and handles subsequent updates
        } catch {
          addMessage({
            role: "assistant",
            content: "抱歉，出了点问题。请稍后再试。",
          })
          setRunning(false)
          setStreaming(false)
        } finally {
          setLoading(false)
        }
        return
      }

      // Start a new conversation (new plan)
      chatReset()
      agentReset()
      planReset()

      // Add user message + assistant placeholder immediately
      addMessage({ role: "user", content: text })
      addMessage({ role: "assistant", content: "" })
      setRunning(true)
      setStreaming(true)

      try {
        const req: PlanCreateRequest = { user_input: text }
        if (geo.lat !== null && geo.lng !== null) {
          req.lat = geo.lat
          req.lng = geo.lng
        }
        const resp = await createPlan(req)
        const data: any = resp.data ?? resp
        if (data?.plan_id) {
          // Store planId so usePlanSSE connects to the SSE stream
          usePlanStore.setState({ planId: data.plan_id })
          // Link conversation to plan for sidebar switching
          setConversationMeta(data.plan_id)
        }
      } catch {
        addMessage({
          role: "assistant",
          content: "抱歉，出了点问题。请稍后再试。",
        })
        setRunning(false)
        setStreaming(false)
      } finally {
        setLoading(false)
      }
    },
    [addMessage, chatReset, agentReset, planReset, setRunning, setStreaming, setConversationMeta, geo.lat, geo.lng],
  )

  return (
    <div className="h-full flex bg-stone-50">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <ChatView />
        <ChatInput onSend={handleSend} disabled={loading} />
      </main>
    </div>
  )
}
