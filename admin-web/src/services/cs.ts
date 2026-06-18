import request from '@/utils/request';

const BASE = '/admin/cs';

// ── Tickets ──────────────────────────────────────────────────────────────

export const getTicketListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.CsTicket>>>(`${BASE}/tickets`, { params });

export const getTicketDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.CsTicket>>(`${BASE}/tickets/${id}`);

export const updateTicketAPI = (id: string, data: Record<string, unknown>) =>
  request.put<API.ApiResponse<API.CsTicket>>(`${BASE}/tickets/${id}`, data);

export const assignTicketAPI = (id: string, data: { agentId?: string; action: string }) =>
  request.post(`${BASE}/tickets/${id}/assign`, data);

export const resolveTicketAPI = (id: string, data: { resolution: string; satisfactionScore?: number }) =>
  request.post(`${BASE}/tickets/${id}/resolve`, data);

// ── Messages ─────────────────────────────────────────────────────────────

export const getTicketMessagesAPI = (id: string, params?: { limit?: number; before?: string }) =>
  request.get<API.ApiResponse<{ ticketId: string; messages: API.CsMessage[] }>>(`${BASE}/tickets/${id}/messages`, { params });

export const sendTicketMessageAPI = (id: string, data: { content: string; contentType?: string }) =>
  request.post<API.ApiResponse<API.CsMessage>>(`${BASE}/tickets/${id}/messages`, data);

// ── Agents ───────────────────────────────────────────────────────────────

export const getAgentsAPI = () =>
  request.get(`${BASE}/agents`);

export const updateAgentStatusAPI = (data: { status: string; currentTicketId?: string }) =>
  request.put(`${BASE}/agents/me/status`, data);

// ── Notifications ────────────────────────────────────────────────────────

export const getNotificationsAPI = (params?: { isRead?: boolean; limit?: number }) =>
  request.get(`${BASE}/notifications`, { params });

export const markNotificationReadAPI = (id: string) =>
  request.put(`${BASE}/notifications/${id}/read`);

export const markAllNotificationsReadAPI = () =>
  request.put(`${BASE}/notifications/read-all`);

// ── Stats ────────────────────────────────────────────────────────────────

export const getCsStatsAPI = () =>
  request.get(`${BASE}/stats`);
