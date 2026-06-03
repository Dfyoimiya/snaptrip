import { useEffect, useRef, useMemo } from "react"
import { useChatStore } from "../../stores/chatStore"
import { useAgentStore } from "../../stores/agentStore"
import { MessageBubble } from "./MessageBubble"
import { QuestionCard } from "./QuestionCard"
import { Loader2 } from "lucide-react"

export function ChatView() {
  const allMessages = useChatStore((s) => s.messages)
  const currentConvId = useChatStore((s) => s.currentConversationId)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const isRunning = useAgentStore((s) => s.isRunning)
  const bottomRef = useRef<HTMLDivElement>(null)

  const messages = useMemo(
    () => allMessages.filter((m) => m.conversationId === currentConvId),
    [allMessages, currentConvId],
  )

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isStreaming])

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Welcome */}
        {messages.length === 0 && !isRunning && (
          <div className="text-center py-16">
            <h2 className="text-lg font-semibold text-stone-700 mb-2">
              周末想去哪儿？
            </h2>
            <p className="text-sm text-stone-500 leading-relaxed max-w-sm mx-auto">
              告诉我你的需求，比如人数、预算、偏好…<br />
              我来帮你搜罗周边好去处，规划最合适的行程。
            </p>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg) => (
          <div key={msg.id} className="animate-slide-up">
            <MessageBubble message={msg} />
          </div>
        ))}

        {/* Question card (appears below last assistant message) */}
        <QuestionCard />

        {/* Streaming / loading indicator — only show when no skeleton bubble is shown */}
        {isStreaming && !(messages.at(-1)?.role === "assistant" && !messages.at(-1)?.content) && (
          <div className="flex items-center gap-2 text-stone-400 text-xs pl-10">
            <Loader2 size={14} className="animate-spin" />
            正在思考…
          </div>
        )}

        {/* Running without streaming — only show when no skeleton bubble is shown */}
        {isRunning && !isStreaming && messages.length > 0 && !(messages.at(-1)?.role === "assistant" && !messages.at(-1)?.content) && (
          <div className="flex items-center gap-2 text-stone-400 text-xs pl-10">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-fade-pulse" />
            处理中…
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
