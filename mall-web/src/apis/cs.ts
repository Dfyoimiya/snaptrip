/**
 * ============================================
 * 客服 Chat API
 * Portal AI 客服对话接口
 * ============================================
 */

import { post } from '@/utils/request'

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
