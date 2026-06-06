import { useChatStore } from "../../stores/chatStore"
import { useAgentStore } from "../../stores/agentStore"
import { usePlanStore } from "../../stores/planStore"
import { getPlan } from "../../api/plan"
import { MessageSquare, Plus } from "lucide-react"
import type { ChatMessage } from "../../stores/chatStore"

function deriveConversations(messages: ChatMessage[]) {
  const map = new Map<string, { id: string; title: string; timestamp: number }>()
  for (const msg of messages) {
    if (msg.role === "user" && !map.has(msg.conversationId)) {
      map.set(msg.conversationId, {
        id: msg.conversationId,
        title: msg.content.slice(0, 40) + (msg.content.length > 40 ? "\u2026" : ""),
        timestamp: msg.timestamp,
      })
    }
  }
  return [...map.values()].sort((a, b) => b.timestamp - a.timestamp)
}

export function Sidebar() {
  const messages = useChatStore((s) => s.messages)
  const currentConvId = useChatStore((s) => s.currentConversationId)
  const newConversation = useChatStore((s) => s.newConversation)
  const switchConversation = useChatStore((s) => s.switchConversation)
  const getConversationMeta = useChatStore((s) => s.getConversationMeta)
  const agentReset = useAgentStore((s) => s.reset)
  const planReset = usePlanStore((s) => s.reset)

  const conversations = deriveConversations(messages)

  async function handleSwitchConv(convId: string) {
    switchConversation(convId)
    useAgentStore.getState().setInterruptPayload(null)
    const meta = getConversationMeta(convId)
    if (meta?.planId) {
      // Restore plan state for this conversation
      usePlanStore.setState({ planId: meta.planId })
      try {
        const resp = await getPlan(meta.planId)
        const data: any = (resp as any).data ?? resp
        if (data?.plan_id) {
          usePlanStore.getState().setPlan(data)
        }
      } catch {
        // plan may no longer exist — that's ok
      }
    } else {
      planReset()
      useAgentStore.getState().setInterruptPayload(null)
    }
  }

  function handleNewChat() {
    newConversation()
    agentReset()
    planReset()
  }

  return (
    <aside className="w-64 h-full flex flex-col bg-stone-100 border-r border-stone-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-stone-200">
        <h1 className="text-sm font-semibold text-stone-700 tracking-tight">
          SnapTrip
        </h1>
        <p className="text-[10px] text-stone-400 mt-0.5">
          本地出行智能助手
        </p>
      </div>

      {/* New Chat button */}
      <div className="px-3 py-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-stone-600 bg-white border border-stone-200 rounded-lg hover:bg-stone-50 hover:border-stone-300 transition-colors"
        >
          <Plus size={14} />
          新对话
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 pb-3">
        {conversations.length === 0 ? (
          <p className="text-[11px] text-stone-400 px-1 py-6 text-center">
            还没有对话记录
          </p>
        ) : (
          <div className="space-y-0.5">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => handleSwitchConv(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 ${
                  conv.id === currentConvId
                    ? "bg-stone-200/80 text-stone-800 font-medium"
                    : "text-stone-600 hover:bg-stone-200/60"
                }`}
              >
                <MessageSquare size={12} className="shrink-0 text-stone-400" />
                <span className="truncate">{conv.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-stone-200">
        <p className="text-[10px] text-stone-400 text-center">
          SnapTrip v2
        </p>
      </div>
    </aside>
  )
}
