import request from '@/utils/request';

// Return apply
export const getReturnApplyListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.ReturnApply>>>('/admin/return-applies', { params });

export const getReturnApplyDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.ReturnApply>>(`/admin/return-applies/${id}`);

export const updateReturnApplyStatusAPI = (id: string, data: API.ReturnApplyStatusUpdate) =>
  request.patch(`/admin/return-applies/${id}/status`, data);

export const deleteReturnAppliesAPI = (ids: string[]) =>
  request.delete('/admin/return-applies', { params: { ids } });

// Return reasons
export const getReturnReasonListAPI = () =>
  request.get<API.ApiResponse<API.ReturnReason[]>>('/admin/return-reasons');

export const createReturnReasonAPI = (data: { name: string; sort?: number }) =>
  request.post('/admin/return-reasons', data);

export const updateReturnReasonAPI = (id: string, data: { name?: string; sort?: number }) =>
  request.put(`/admin/return-reasons/${id}`, data);

export const deleteReturnReasonAPI = (id: string) =>
  request.delete(`/admin/return-reasons/${id}`);

// Order settings
export const getOrderSettingAPI = () =>
  request.get('/admin/order-setting');

export const updateOrderSettingAPI = (data: Record<string, unknown>) =>
  request.put('/admin/order-setting', data);
