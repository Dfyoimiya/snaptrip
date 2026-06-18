import request from '@/utils/request';

const BASE = '/admin/brands';

export const getBrandListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Brand>>>(BASE, { params });

export const getAllBrandsAPI = () =>
  request.get<API.ApiResponse<API.Brand[]>>(`${BASE}/all`);

export const getBrandDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Brand>>(`${BASE}/${id}`);

export const createBrandAPI = (data: API.BrandCreate) =>
  request.post<API.ApiResponse<API.Brand>>(BASE, data);

export const updateBrandAPI = (id: string, data: API.BrandUpdate) =>
  request.put<API.ApiResponse<API.Brand>>(`${BASE}/${id}`, data);

export const deleteBrandAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

export const toggleBrandStatusAPI = (id: string, field: string, status: number) =>
  request.patch(`${BASE}/${id}/status`, null, { params: { field, status } });
