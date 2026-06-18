import request from '@/utils/request';

const BASE = '/admin/members';

export const getMemberListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Member>>>(BASE, { params });

export const getMemberDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Member>>(`${BASE}/${id}`);

export const toggleMemberStatusAPI = (id: string, isActive: boolean) =>
  request.patch(`${BASE}/${id}/status`, null, { params: { is_active: isActive } });
