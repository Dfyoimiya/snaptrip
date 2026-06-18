import request from '@/utils/request';

const BASE = '/admin/categories';

export const getCategoryListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Category>>>(BASE, { params });

export const getCategoryTreeAPI = () =>
  request.get<API.ApiResponse<API.CategoryTree[]>>(`${BASE}/tree`);

export const getCategoryDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Category>>(`${BASE}/${id}`);

export const createCategoryAPI = (data: API.CategoryCreate) =>
  request.post<API.ApiResponse<API.Category>>(BASE, data);

export const updateCategoryAPI = (id: string, data: API.CategoryUpdate) =>
  request.put<API.ApiResponse<API.Category>>(`${BASE}/${id}`, data);

export const deleteCategoryAPI = (id: string, force?: boolean) =>
  request.delete(`${BASE}/${id}`, { params: { force } });

export const toggleCategoryStatusAPI = (id: string, field: string, status: number) =>
  request.patch(`${BASE}/${id}/status`, null, { params: { field, status } });

export const updateCategorySortAPI = (id: string, sort: number) =>
  request.patch(`${BASE}/${id}/sort`, null, { params: { sort } });
