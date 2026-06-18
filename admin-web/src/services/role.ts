import request from '@/utils/request';

const BASE = '/role';

export const getRoleListAllAPI = () =>
  request.get<API.ApiResponse<API.Role[]>>(`${BASE}/listAll`);

export const getRoleListAPI = (params: Record<string, number>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Role>>(`${BASE}/list`, { params });

export const createRoleAPI = (data: API.RoleCreate) =>
  request.post<API.ApiResponse<API.Role>>(`${BASE}/create`, data);

export const updateRoleAPI = (id: string, data: Partial<API.RoleCreate>) =>
  request.post<API.ApiResponse<API.Role>>(`${BASE}/update/${id}`, data);

export const updateRoleStatusAPI = (id: string, status: number) =>
  request.post(`${BASE}/updateStatus/${id}`, null, { params: { status } });

export const deleteRolesAPI = (ids: string[]) =>
  request.post(`${BASE}/delete`, null, { params: { ids } });

export const getRoleMenuListAPI = (roleId: string) =>
  request.get(`${BASE}/listMenu/${roleId}`);

export const getRoleResourceListAPI = (roleId: string) =>
  request.get(`${BASE}/listResource/${roleId}`);

export const allocRoleMenuAPI = (roleId: string, menuIds: string[]) =>
  request.post(`${BASE}/allocMenu`, { role_id: roleId, menu_ids: menuIds });

export const allocRoleResourceAPI = (roleId: string, resourceIds: string[]) =>
  request.post(`${BASE}/allocResource`, { role_id: roleId, resource_ids: resourceIds });
