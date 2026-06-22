/**
 * ============================================
 * 客服聊天 Store (Pinia)
 * 管理聊天面板状态、消息历史、工单会话持久化
 * ============================================
 */

import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  intent?: string
}

const STORAGE_KEY = 'snaptrip_cs_chat_messages'
const SESSION_KEY = 'snaptrip_cs_session_id'
const TICKET_KEY = 'snaptrip_cs_ticket_id'

function loadMessages(): ChatMessage[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch { /* ignore */ }
  return [
    {
      role: 'system',
      content: '你好！我是 SnapTrip 在线客服，请问有什么可以帮你的？',
      timestamp: Date.now(),
    },
  ]
}

function loadSessionId(): string {
  try {
    const saved = localStorage.getItem(SESSION_KEY)
    if (saved) return saved
  } catch { /* ignore */ }
  const id = `cs_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(SESSION_KEY, id)
  return id
}

function loadTicketId(): string | null {
  try {
    const saved = localStorage.getItem(TICKET_KEY)
    return saved || null
  } catch {
    return null
  }
}

export const useChatStore = defineStore('chat', () => {
  const isOpen = ref(false)
  const loading = ref(false)
  const sessionId = ref(loadSessionId())
  const ticketId = ref<string | null>(loadTicketId())
  const messages = ref<ChatMessage[]>(loadMessages())

  watch(messages, (val) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(val)) } catch { /* ignore */ }
  }, { deep: true })

  function openChat() {
    isOpen.value = true
  }

  function closeChat() {
    isOpen.value = false
  }

  function toggleChat() {
    isOpen.value = !isOpen.value
  }

  function addMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  function setTicketId(id: string) {
    ticketId.value = id
    try { localStorage.setItem(TICKET_KEY, id) } catch { /* ignore */ }
  }

  function clearMessages() {
    messages.value = [
      {
        role: 'system',
        content: '你好！我是 SnapTrip 在线客服，请问有什么可以帮你的？',
        timestamp: Date.now(),
      },
    ]
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
  }

  return {
    isOpen,
    loading,
    sessionId,
    ticketId,
    messages,
    openChat,
    closeChat,
    toggleChat,
    addMessage,
    setTicketId,
    clearMessages,
  }
})
