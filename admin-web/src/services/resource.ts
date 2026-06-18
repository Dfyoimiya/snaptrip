import request from '@/utils/request';

// Resource categories
export const getResourceCategoriesAPI = () =>
  request.get<API.ApiResponse<API.ResourceCategory[]>>('/resourceCategory/listAll');

export const createResourceCategoryAPI = (data: { name: string; sort?: number }) =>
  request.post('/resourceCategory/create', data);

export const updateResourceCategoryAPI = (id: string, data: { name?: string; sort?: number }) =>
  request.post(`/resourceCategory/update/${id}`, data);

export const deleteResourceCategoryAPI = (id: string) =>
  request.post(`/resourceCategory/delete/${id}`);

// Resources
export const getResourceListAllAPI = () =>
  request.get<API.ApiResponse<API.Resource[]>>('/resource/listAll');

export const getResourceListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Resource>>('/resource/list', { params });

export const createResourceAPI = (data: { categoryId?: string; name: string; url?: string; description?: string }) =>
  request.post('/resource/create', data);

export const updateResourceAPI = (id: string, data: Record<string, unknown>) =>
  request.post(`/resource/update/${id}`, data);

export const deleteResourceAPI = (id: string) =>
  request.post(`/resource/delete/${id}`);
