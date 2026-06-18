import request from '@/utils/request';

const BASE = '/admin';

export const getAdminListAPI = (params: Record<string, number>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.AdminUser>>>(`${BASE}/list`, { params });

export const registerAdminAPI = (data: { email: string; password: string; roleIds: string[] }) =>
  request.post(`${BASE}/register`, data);

export const updateAdminAPI = (id: string, data: { email?: string; password?: string; isActive?: boolean; roleIds?: string[] }) =>
  request.post(`${BASE}/update/${id}`, data);

export const updateAdminStatusAPI = (id: string, status: number) =>
  request.post(`${BASE}/updateStatus/${id}`, null, { params: { status } });

export const deleteAdminAPI = (id: string) =>
  request.post(`${BASE}/delete/${id}`);

export const getAdminRolesAPI = (adminId: string) =>
  request.get<API.ApiResponse<API.Role[]>>(`${BASE}/role/${adminId}`);

export const updateAdminRolesAPI = (data: { adminId: string; roleIds: string[] }) =>
  request.post(`${BASE}/role/update`, data);
