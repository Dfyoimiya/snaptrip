import request from '@/utils/request';

const BASE = '/admin/products';

export const getProductListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Product>>>(BASE, { params });

export const getProductDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Product>>(`${BASE}/${id}`);

export const createProductAPI = (data: API.ProductCreate) =>
  request.post<API.ApiResponse<API.Product>>(BASE, data);

export const updateProductAPI = (id: string, data: API.ProductUpdate) =>
  request.put<API.ApiResponse<API.Product>>(`${BASE}/${id}`, data);

export const deleteProductAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

export const toggleProductStatusAPI = (id: string, status: number) =>
  request.patch(`${BASE}/${id}/status`, null, { params: { status } });

export const batchProductStatusAPI = (ids: string[], status: number) =>
  request.patch(`${BASE}/batch-status`, null, { params: { ids, status } });

export const toggleProductNewAPI = (id: string, status: number) =>
  request.patch(`${BASE}/${id}/new`, null, { params: { status } });

export const toggleProductRecommendAPI = (id: string, status: number) =>
  request.patch(`${BASE}/${id}/recommend`, null, { params: { status } });

export const verifyProductAPI = (id: string, status: number, reason?: string) =>
  request.patch(`${BASE}/${id}/verify`, null, { params: { status, reason } });

export const addSkuAPI = (productId: string, data: API.SkuCreate) =>
  request.post(`${BASE}/${productId}/skus`, data);

export const updateSkuAPI = (productId: string, skuId: string, data: Partial<API.SkuCreate>) =>
  request.put(`${BASE}/${productId}/skus/${skuId}`, data);

export const deleteSkuAPI = (productId: string, skuId: string) =>
  request.delete(`${BASE}/${productId}/skus/${skuId}`);

export const updateProductAttributesAPI = (id: string, data: Record<string, string>) =>
  request.put(`${BASE}/${id}/attributes`, data);

export const syncProductEsAPI = (id: string) =>
  request.post(`${BASE}/${id}/sync-es`);
