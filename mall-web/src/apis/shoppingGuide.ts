/**
 * ============================================
 * 帮我挑 — 导购 Agent API
 * ============================================
 */
import { get, post, del } from '@/utils/request'
import { useMemberStore } from '@/stores/member'

// ── 类型定义 ──

export interface ShoppingContext {
  current_product_id?: string | null
  current_category?: string | null
  search_query?: string | null
}

export interface ShoppingGuideChatRequest {
  message: string
  session_id?: string | null
  context?: ShoppingContext | null
  mode?: 'auto' | 'info' | 'product'
}

export interface RecommendedProduct {
  name: string
  price: number
  originalPrice: number
  discount: string
  link: string
  highlights: string[]
  /** 商品图片 URL（可选，用于 ProductCard 展示） */
  imageUrl?: string | null
  /** 商品 ID（可选，优先使用；否则从 link 提取） */
  productId?: string | null
  /** 品牌名称 */
  brandName?: string | null
  /** 销量 */
  saleCount?: number | null
}

export interface ShoppingGuideChatResponse {
  reply: string
  sessionId: string
  products: RecommendedProduct[]
  followUpQuestions: string[]
}

export interface ShoppingGuideSession {
  id: string
  userId: string
  createdAt: string
  updatedAt: string
  messageCount: number
  summary: string | null
}

export interface SessionDetail {
  id: string
  userId: string
  messageCount: number
  messages: Array<{ role: string; content: string; timestamp?: number }>
  summary: string | null
}

// ── API ──

const BASE = '/api/v1/shopping-guide'

export const shoppingGuideChatAPI = (data: ShoppingGuideChatRequest) =>
  post<ShoppingGuideChatResponse>(`${BASE}/chat`, data, { timeout: 60_000 })

export const listSessionsAPI = () =>
  get<{ sessions: ShoppingGuideSession[]; total: number }>(`${BASE}/sessions`)

export const getSessionAPI = (sessionId: string) =>
  get<SessionDetail>(`${BASE}/sessions/${sessionId}`)

export const deleteSessionAPI = (sessionId: string) =>
  del<{ deleted: boolean; session_id: string }>(`${BASE}/sessions/${sessionId}`)

// ── 流式 API ──

export interface StreamCallbacks {
  onToken: (token: string) => void
  onDone: (payload: { sessionId: string; products: RecommendedProduct[]; followUpQuestions: string[] }) => void
  onError: (error: string) => void
}

/**
 * 流式导购对话 — 使用 fetch + ReadableStream 消费 SSE 端点。
 * 不经过 Axios 拦截器（JSON→camelCase 对 SSE 无效），token 手动注入。
 */
export async function shoppingGuideChatStreamAPI(
  data: ShoppingGuideChatRequest,
  callbacks: StreamCallbacks,
): Promise<void> {
  const memberStore = useMemberStore()
  const token = memberStore.token

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'source-client': 'pc',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch('/api/v1/shopping-guide/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    callbacks.onError(`HTTP ${response.status}: ${response.statusText}`)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError('Stream not supported')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // Keep the last (possibly incomplete) line in the buffer
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6).trim()
        if (!jsonStr) continue

        try {
          const event = JSON.parse(jsonStr)
          switch (event.type) {
            case 'token':
              callbacks.onToken(event.content)
              break
            case 'done':
              callbacks.onDone({
                sessionId: event.session_id,
                products: event.products || [],
                followUpQuestions: event.follow_up_questions || [],
              })
              break
            case 'error':
              callbacks.onError(event.message || 'Unknown error')
              break
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
