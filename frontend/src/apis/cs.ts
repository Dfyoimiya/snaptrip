import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type {
  CsTicket,
  TicketListQuery,
  TicketUpdateData,
  CsMessage,
  AgentStatus,
  CsNotification,
  CsStats,
} from '@/types/cs'

// ════════════════════════════════════════════════════════════════════════════
//  工单管理
// ════════════════════════════════════════════════════════════════════════════

/** GET /admin/cs/tickets — 工单分页列表 */
export function getTicketListAPI(params: TicketListQuery) {
  return request<CommonResult<CommonPage<CsTicket>>>({
    url: '/admin/cs/tickets',
    method: 'get',
    params,
  })
}

/** GET /admin/cs/tickets/{id} — 工单详情 */
export function getTicketDetailAPI(id: string) {
  return request<CommonResult<CsTicket>>({
    url: `/admin/cs/tickets/${id}`,
    method: 'get',
  })
}

/** PUT /admin/cs/tickets/{id} — 更新工单 */
export function updateTicketAPI(id: string, data: TicketUpdateData) {
  return request<CommonResult<CsTicket>>({
    url: `/admin/cs/tickets/${id}`,
    method: 'put',
    data,
  })
}

/** POST /admin/cs/tickets/{id}/assign — 指派/认领工单 */
export function assignTicketAPI(id: string, agentId?: string, action = 'assign') {
  return request<CommonResult<CsTicket>>({
    url: `/admin/cs/tickets/${id}/assign`,
    method: 'post',
    data: { agent_id: agentId, action },
  })
}

/** POST /admin/cs/tickets/{id}/resolve — 解决/关闭工单 */
export function resolveTicketAPI(id: string, resolution: string, satisfactionScore?: number) {
  return request<CommonResult<CsTicket>>({
    url: `/admin/cs/tickets/${id}/resolve`,
    method: 'post',
    data: { resolution, satisfaction_score: satisfactionScore },
  })
}

// ════════════════════════════════════════════════════════════════════════════
//  聊天消息
// ════════════════════════════════════════════════════════════════════════════

/** GET /admin/cs/tickets/{id}/messages — 获取聊天历史 */
export function getTicketMessagesAPI(ticketId: string, limit = 50, before?: string) {
  return request<CommonResult<{ ticket_id: string; messages: CsMessage[] }>>({
    url: `/admin/cs/tickets/${ticketId}/messages`,
    method: 'get',
    params: { limit, before },
  })
}

/** POST /admin/cs/tickets/{id}/messages — 发送消息 */
export function sendTicketMessageAPI(ticketId: string, content: string, contentType = 'text') {
  return request<CommonResult<CsMessage>>({
    url: `/admin/cs/tickets/${ticketId}/messages`,
    method: 'post',
    data: { content, content_type: contentType },
  })
}

/** SSE 订阅 — 工单实时消息流 */
export function getTicketStreamUrl(ticketId: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/admin/cs/tickets/${ticketId}/stream`
}

// ════════════════════════════════════════════════════════════════════════════
//  坐席状态
// ════════════════════════════════════════════════════════════════════════════

/** GET /admin/cs/agents — 在线坐席列表 */
export function getAgentsAPI() {
  return request<CommonResult<AgentStatus[]>>({
    url: '/admin/cs/agents',
    method: 'get',
  })
}

/** PUT /admin/cs/agents/me/status — 更新坐席状态 */
export function updateAgentStatusAPI(status: string, currentTicketId?: string) {
  return request<CommonResult<AgentStatus>>({
    url: '/admin/cs/agents/me/status',
    method: 'put',
    data: { status, current_ticket_id: currentTicketId },
  })
}

// ════════════════════════════════════════════════════════════════════════════
//  通知
// ════════════════════════════════════════════════════════════════════════════

/** GET /admin/cs/notifications — 通知列表 */
export function getNotificationsAPI(isRead?: boolean, limit = 50) {
  return request<CommonResult<{ items: CsNotification[]; unread_count: number; total: number }>>({
    url: '/admin/cs/notifications',
    method: 'get',
    params: { is_read: isRead, limit },
  })
}

/** PUT /admin/cs/notifications/{id}/read — 标记已读 */
export function markNotificationReadAPI(id: string) {
  return request<CommonResult<CsNotification>>({
    url: `/admin/cs/notifications/${id}/read`,
    method: 'put',
  })
}

/** PUT /admin/cs/notifications/read-all — 全部已读 */
export function markAllNotificationsReadAPI() {
  return request<CommonResult<{ message: string }>>({
    url: '/admin/cs/notifications/read-all',
    method: 'put',
  })
}

/** SSE 订阅 — 通知流 */
export function getNotificationStreamUrl(): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/admin/cs/notifications/stream`
}

// ════════════════════════════════════════════════════════════════════════════
//  统计
// ════════════════════════════════════════════════════════════════════════════

/** GET /admin/cs/stats — 客服统计 */
export function getCsStatsAPI() {
  return request<CommonResult<CsStats>>({
    url: '/admin/cs/stats',
    method: 'get',
  })
}
