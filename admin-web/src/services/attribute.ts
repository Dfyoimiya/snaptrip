import request from '@/utils/request';

const BASE = '/admin/product-attributes';

export const getAttributeListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.ProductAttribute>>>(BASE, { params });

export const getAttributeCategoriesAPI = () =>
  request.get<API.ApiResponse<{ id: string; name: string; attributeCount: number; productAttributeList: API.ProductAttribute[] }[]>>(`${BASE}/categories`);

export const getAttributeDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.ProductAttribute>>(`${BASE}/${id}`);

export const createAttributeAPI = (data: API.ProductAttributeCreate) =>
  request.post<API.ApiResponse<API.ProductAttribute>>(BASE, data);

export const updateAttributeAPI = (id: string, data: Partial<API.ProductAttributeCreate>) =>
  request.put<API.ApiResponse<API.ProductAttribute>>(`${BASE}/${id}`, data);

export const deleteAttributeAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

// Attribute category CRUD
export const createAttrCategoryAPI = (name: string) =>
  request.post(`${BASE}/categories`, null, { params: { name } });

export const updateAttrCategoryAPI = (id: string, name: string) =>
  request.put(`${BASE}/categories/${id}`, null, { params: { name } });

export const deleteAttrCategoryAPI = (id: string) =>
  request.delete(`${BASE}/categories/${id}`);
