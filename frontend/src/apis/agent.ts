import request from '@/utils/request'
import type { CommonResult } from '@/types/common'

export interface AgentChatRequest {
  message: string
  session_id?: string
}

export interface AgentChatResponse {
  reply: string
  intent: string
  data?: Record<string, any> | null
}

export function adminAgentChatAPI(data: AgentChatRequest) {
  return request<CommonResult<AgentChatResponse>>({
    url: '/admin/agent/chat',
    method: 'post',
    data,
    timeout: 60000,  // Agent needs multiple LLM calls, can take 10-30s
  })
}
