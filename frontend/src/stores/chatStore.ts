import { create } from "zustand"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: number
  conversationId: string
  /** Plan data attached to an assistant message */
  plan?: PlanPreview
}

export interface PlanPreview {
  summary?: string
  total_cost?: number
  slots?: Array<{
    time_start?: string
    time_end?: string
    action?: string
    place?: string
    estimated_cost?: number
    note?: string
  }>
}

interface ConversationMeta {
  planId: string
  title: string
  createdAt: number
}

const conversationMetaMap = new Map<string, ConversationMeta>()

let _msgId = 0
let _convSeq = 0

function nextMsgId(): string {
  return `msg-${++_msgId}-${Date.now()}`
}

function nextConvId(): string {
  return `conv-${++_convSeq}-${Date.now()}`
}

interface ChatStore {
  messages: ChatMessage[]
  isStreaming: boolean
  currentConversationId: string

  addMessage: (msg: Omit<ChatMessage, "id" | "timestamp" | "conversationId">) => void
  updateLastAssistant: (content: string) => void
  attachPlanToLastAssistant: (plan: PlanPreview) => void
  setStreaming: (v: boolean) => void

  newConversation: () => string
  switchConversation: (convId: string) => void
  setConversationMeta: (planId: string, title?: string) => void
  getConversationMeta: (convId: string) => ConversationMeta | undefined
  reset: () => void
}

const INITIAL_CONV_ID = nextConvId()

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentConversationId: INITIAL_CONV_ID,

  addMessage: (msg) =>
    set((s) => ({
      messages: [
        ...s.messages,
        {
          ...msg,
          id: nextMsgId(),
          timestamp: Date.now(),
          conversationId: s.currentConversationId,
        },
      ],
    })),

  updateLastAssistant: (content) =>
    set((s) => {
      const msgs = [...s.messages]
      // Find the last assistant message in the CURRENT conversation
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (
          msgs[i].role === "assistant" &&
          msgs[i].conversationId === s.currentConversationId
        ) {
          msgs[i] = { ...msgs[i], content }
          break
        }
      }
      return { messages: msgs }
    }),

  attachPlanToLastAssistant: (plan) =>
    set((s) => {
      const msgs = [...s.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (
          msgs[i].role === "assistant" &&
          msgs[i].conversationId === s.currentConversationId
        ) {
          msgs[i] = { ...msgs[i], plan }
          break
        }
      }
      return { messages: msgs }
    }),

  setStreaming: (v) => set({ isStreaming: v }),

  newConversation: () => {
    const convId = nextConvId()
    set({ currentConversationId: convId })
    return convId
  },

  switchConversation: (convId) => {
    set({ currentConversationId: convId })
  },

  setConversationMeta: (planId, title) => {
    const { currentConversationId, messages } = get()
    const existing = conversationMetaMap.get(currentConversationId)
    const firstUserMsg = messages.find(
      (m) => m.role === "user" && m.conversationId === currentConversationId
    )
    conversationMetaMap.set(currentConversationId, {
      planId,
      title: title ?? existing?.title ?? firstUserMsg?.content.slice(0, 40) ?? "新对话",
      createdAt: existing?.createdAt ?? Date.now(),
    })
  },

  getConversationMeta: (convId) => {
    return conversationMetaMap.get(convId)
  },

  reset: () => {
    const convId = nextConvId()
    set({ isStreaming: false, currentConversationId: convId })
  },
}))
