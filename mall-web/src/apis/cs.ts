/**
 * ============================================
 * 客服 Chat API
 * Portal C2B 客服接口 — 工单聊天 & AI 对话
 * ============================================
 */

import request, { post } from '@/utils/request'
import type { CommonResult } from '@/types/common'

export interface CsChatRequest {
  message: string
  session_id?: string
}

export interface CsChatResponse {
  reply: string
  intent: string
  data?: Record<string, unknown> | null
}

/** Portal AI 客服对话 — POST /portal/cs/chat */
export const portalCsChatAPI = (data: CsChatRequest) => {
  return post<CsChatResponse>('/api/v1/portal/cs/chat', data, {
    timeout: 60000,
  })
}

// ── Ticket-based human CS chat ────────────────────────────────────────────────

export interface EnsureSessionResponse {
  id: string
  status: string
  title?: string
  created_at?: string
}

/** POST /portal/cs/session/ensure — 获取或创建活跃咨询工单 */
export function ensureSessionAPI() {
  return post<CommonResult<EnsureSessionResponse>>('/api/v1/portal/cs/session/ensure')
}

export interface TicketMessage {
  id: string
  ticket_id: string
  sender_type: 'user' | 'agent' | 'system'
  sender_id: string | null
  content: string
  content_type: string
  metadata?: Record<string, unknown> | null
  created_at: string
}

export interface TicketMessagesResponse {
  ticket_id: string
  messages: TicketMessage[]
}

/** GET /portal/cs/tickets/{id}/messages — 获取工单聊天历史 */
export function getPortalTicketMessagesAPI(ticketId: string, limit = 50) {
  return request<CommonResult<TicketMessagesResponse>>({
    url: `/api/v1/portal/cs/tickets/${ticketId}/messages`,
    method: 'get',
    params: { limit },
  })
}

/** POST /portal/cs/tickets/{id}/messages — 用户发送消息 */
export function sendPortalTicketMessageAPI(ticketId: string, content: string) {
  return post<CommonResult<TicketMessage>>(`/api/v1/portal/cs/tickets/${ticketId}/messages`, {
    content,
    content_type: 'text',
  })
}

/** SSE 订阅 — 用户侧工单消息流
 *  EventSource 不支持自定 义 Header，通过 query param 传递 JWT token 进行认证 */
export function getPortalTicketStreamUrl(ticketId: string, token?: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  let url = `${baseUrl}/api/v1/portal/cs/chat/${ticketId}`
  if (token) {
    url += `?token=${encodeURIComponent(token)}`
  }
  return url
}
