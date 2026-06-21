/**
 * ============================================
 * 帮我挑 — 导购聊天状态管理
 *
 * 持久化到 localStorage:
 *   - 消息历史 (按 session)
 *   - 当前 session_id
 * ============================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useRouter } from 'vue-router'
import {
  shoppingGuideChatAPI,
  shoppingGuideChatStreamAPI,
  listSessionsAPI,
  getSessionAPI,
  deleteSessionAPI,
  type ShoppingContext,
  type RecommendedProduct,
  type ShoppingGuideSession,
} from '@/apis/shoppingGuide'

export type { RecommendedProduct }

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  /** 导购推荐的关联商品 */
  products?: RecommendedProduct[]
  /** AI 建议的追问 */
  followUps?: string[]
}

const STORAGE_KEY = '_snaptrip_shopping_guide'
const MAX_MESSAGES = 200

function loadMessages(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

function saveMessages(msgs: ChatMessage[]) {
  try {
    const trimmed = msgs.slice(-MAX_MESSAGES)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
  } catch { /* ignore */ }
}

export const useShoppingGuideStore = defineStore('shoppingGuide', () => {
  // ── State ──
  const isOpen = ref(false)
  const loading = ref(false)
  const sessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>(loadMessages())
  const sessions = ref<ShoppingGuideSession[]>([])
  const sessionsLoading = ref(false)

  // 在 setup 阶段捕获 router 实例，避免后续调用 useRoute() 的 inject() 问题
  const router = useRouter()

  // ── Getters ──
  const hasMessages = computed(() => messages.value.length > 0)
  const lastAssistantMsg = computed(() =>
    [...messages.value].reverse().find(m => m.role === 'assistant'),
  )

  // ── 构建上下文 (通过 router.currentRoute 获取当前路由，避免 useRoute 注入问题) ──
  function _buildContext(): ShoppingContext | null {
    try {
      const route = router.currentRoute.value
      const ctx: ShoppingContext = {}
      if (route.params.id && String(route.path).startsWith('/product/')) {
        ctx.current_product_id = route.params.id as string
      }
      if (String(route.path).startsWith('/category')) {
        ctx.current_category = (route.query.cat as string) || null
      }
      if (route.path === '/search' && route.query.keyword) {
        ctx.search_query = route.query.keyword as string
      }
      if (Object.values(ctx).some(v => v)) return ctx
    } catch { /* route unavailable */ }
    return null
  }

  // ── Actions ──

  function openChat() {
    isOpen.value = true
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '你好！我是 SnapTrip 的 AI 导购助手 ✨\n\n告诉我你想找什么样的商品，比如：\n• 「推荐一款适合学生的笔记本」\n• 「200 元以内的蓝牙耳机」\n• 「最近有什么优惠活动」\n\n我来帮你全网挑选最合适的商品！',
        timestamp: Date.now(),
      })
    }
  }

  function closeChat() {
    isOpen.value = false
  }

  function toggleChat() {
    if (isOpen.value) closeChat()
    else openChat()
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading.value) return

    // 添加用户消息
    const userMsg: ChatMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)
    saveMessages(messages.value)

    // 创建占位 AI 消息（流式填充）
    const aiMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    messages.value.push(aiMsg)
    saveMessages(messages.value)

    loading.value = true
    try {
      await shoppingGuideChatStreamAPI(
        {
          message: text.trim(),
          session_id: sessionId.value,
          context: _buildContext(),
        },
        {
          onToken(token: string) {
            aiMsg.content += token
            saveMessages(messages.value)
          },
          onDone(payload) {
            sessionId.value = payload.sessionId
            if (payload.products?.length) {
              aiMsg.products = payload.products
            }
            if (payload.followUpQuestions?.length) {
              aiMsg.followUps = payload.followUpQuestions
            }
            saveMessages(messages.value)
          },
          onError(error: string) {
            aiMsg.content = error || '抱歉，我暂时无法回复，请稍后再试。'
            saveMessages(messages.value)
          },
        },
      )
    } catch {
      if (!aiMsg.content) {
        aiMsg.content = '抱歉，我暂时无法回复，请稍后再试。'
      }
      saveMessages(messages.value)
    } finally {
      loading.value = false
    }
  }

  async function sendFollowUp(question: string) {
    await sendMessage(question)
  }

  function clearMessages() {
    messages.value = []
    sessionId.value = null
    saveMessages([])
  }

  async function newSession() {
    sessionId.value = null
    messages.value = []
    saveMessages([])
  }

  async function loadSessions() {
    sessionsLoading.value = true
    try {
      const res = await listSessionsAPI()
      sessions.value = res.sessions || []
    } catch {
      sessions.value = []
    } finally {
      sessionsLoading.value = false
    }
  }

  async function loadSession(id: string) {
    loading.value = true
    try {
      const res = await getSessionAPI(id)
      sessionId.value = id
      messages.value = (res.messages || []).map(m => ({
        role: m.role as ChatMessage['role'],
        content: m.content,
        timestamp: m.timestamp || Date.now(),
      }))
      saveMessages(messages.value)
    } catch {
      // session not found or error
    } finally {
      loading.value = false
    }
  }

  async function removeSession(id: string) {
    try {
      await deleteSessionAPI(id)
      if (sessionId.value === id) {
        sessionId.value = null
        messages.value = []
        saveMessages([])
      }
      sessions.value = sessions.value.filter(s => s.id !== id)
    } catch { /* ignore */ }
  }

  return {
    isOpen,
    loading,
    sessionId,
    messages,
    sessions,
    sessionsLoading,
    hasMessages,
    lastAssistantMsg,
    openChat,
    closeChat,
    toggleChat,
    sendMessage,
    sendFollowUp,
    clearMessages,
    newSession,
    loadSessions,
    loadSession,
    removeSession,
  }
})
