/** 客服工单 */
export interface CsTicket {
  id?: string
  orderId?: string
  memberId?: string
  type?: string
  status?: string
  priority?: string
  title?: string
  description?: string
  resolution?: string
  satisfactionScore?: number
  escalatedTo?: string
  assignedAgentId?: string
  slaDeadline?: string
  firstResponseAt?: string
  tags?: string[]
  resolvedAt?: string
  createdAt?: string
  updatedAt?: string
}

/** 工单列表查询 */
export interface TicketListQuery {
  status?: string
  priority?: string
  type?: string
  assignedAgentId?: string
  keyword?: string
  page?: number
  page_size?: number
}

/** 更新工单 */
export interface TicketUpdateData {
  status?: string
  priority?: string
  tags?: string[]
  resolution?: string
  satisfactionScore?: number
}

/** 聊天消息 */
export interface CsMessage {
  id?: string
  ticketId?: string
  senderType?: string
  senderId?: string
  content?: string
  contentType?: string
  metadata?: Record<string, unknown>
  createdAt?: string
}

/** 坐席状态 */
export interface AgentStatus {
  adminId?: string
  status?: string
  currentTicketId?: string
  maxConcurrent?: number
  lastHeartbeat?: string
  skills?: string[]
  adminName?: string
}

/** 通知 */
export interface CsNotification {
  id?: string
  type?: string
  ticketId?: string
  title?: string
  body?: string
  actionUrl?: string
  isRead?: boolean
  readAt?: string
  createdAt?: string
}

/** 客服统计 */
export interface CsStats {
  totalTickets?: number
  openCount?: number
  inProgressCount?: number
  resolvedToday?: number
  avgResponseMinutes?: number
  slaBreachCount?: number
  onlineAgents?: number
}
