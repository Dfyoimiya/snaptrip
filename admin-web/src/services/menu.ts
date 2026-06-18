import request from '@/utils/request';

const BASE = '/menu';

export const getMenuTreeAPI = () =>
  request.get<API.ApiResponse<API.MenuNode[]>>(`${BASE}/treeList`);

export const getMenuChildrenAPI = (parentId: string) =>
  request.get(`${BASE}/list/${parentId}`);

export const getMenuDetailAPI = (id: string) =>
  request.get(`${BASE}/${id}`);

export const createMenuAPI = (data: { parentId?: string; title: string; name?: string; icon?: string; sort?: number; hidden?: number; level?: number }) =>
  request.post(`${BASE}/create`, data);

export const updateMenuAPI = (id: string, data: Record<string, unknown>) =>
  request.post(`${BASE}/update/${id}`, data);

export const deleteMenuAPI = (id: string) =>
  request.post(`${BASE}/delete/${id}`);

export const toggleMenuHiddenAPI = (id: string, hidden: number) =>
  request.post(`${BASE}/updateHidden/${id}`, null, { params: { hidden } });
