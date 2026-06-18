import request from '@/utils/request';

const BASE = '/admin/notices';

export const getNoticeListAPI = (params?: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Notice>>>(BASE, { params });

export const getNoticeDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Notice>>(`${BASE}/${id}`);

export const createNoticeAPI = (data: API.NoticeCreate) =>
  request.post<API.ApiResponse<API.Notice>>(BASE, data);

export const updateNoticeAPI = (id: string, data: API.NoticeUpdate) =>
  request.put<API.ApiResponse<API.Notice>>(`${BASE}/${id}`, data);

export const deleteNoticeAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

export const toggleNoticeStatusAPI = (id: string, status: number) =>
  request.patch(`${BASE}/${id}/status`, null, { params: { status } });
