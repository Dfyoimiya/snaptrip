/**
 * ============================================
 * 导购 Agent Store (Pinia)
 * 管理侧边面板状态、消息历史、会话持久化
 * 与客服 ChatStore 完全隔离
 * ============================================
 */

import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export interface GuideMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

const STORAGE_KEY = 'snaptrip_shopping_chat_messages'
const SESSION_KEY = 'snaptrip_shopping_session_id'

function loadMessages(): GuideMessage[] {
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
      content: '你好！我是 SnapTrip 导购助手。可以帮你搜索商品、推荐好物、对比价格、查询优惠券。告诉我你想买什么吧！',
      timestamp: Date.now(),
    },
  ]
}

function loadSessionId(): string {
  try {
    const saved = localStorage.getItem(SESSION_KEY)
    if (saved) return saved
  } catch { /* ignore */ }
  const id = `sg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(SESSION_KEY, id)
  return id
}

export const useShoppingGuideStore = defineStore('shoppingGuide', () => {
  const isOpen = ref(false)
  const loading = ref(false)
  const sessionId = ref(loadSessionId())
  const messages = ref<GuideMessage[]>(loadMessages())
  const followUpQuestions = ref<string[]>([])

  watch(messages, (val) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(val)) } catch { /* ignore */ }
  }, { deep: true })

  function openPanel() {
    isOpen.value = true
  }

  function closePanel() {
    isOpen.value = false
  }

  function togglePanel() {
    isOpen.value = !isOpen.value
  }

  function addMessage(msg: GuideMessage) {
    messages.value.push(msg)
  }

  function setFollowUpQuestions(questions: string[]) {
    followUpQuestions.value = questions
  }

  function clearFollowUpQuestions() {
    followUpQuestions.value = []
  }

  function clearMessages() {
    messages.value = [
      {
        role: 'system',
        content: '你好！我是 SnapTrip 导购助手。可以帮你搜索商品、推荐好物、对比价格、查询优惠券。告诉我你想买什么吧！',
        timestamp: Date.now(),
      },
    ]
    followUpQuestions.value = []
    // Reset session
    const id = `sg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    sessionId.value = id
    localStorage.setItem(SESSION_KEY, id)
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
  }

  return {
    isOpen,
    loading,
    sessionId,
    messages,
    followUpQuestions,
    openPanel,
    closePanel,
    togglePanel,
    addMessage,
    setFollowUpQuestions,
    clearFollowUpQuestions,
    clearMessages,
  }
})
