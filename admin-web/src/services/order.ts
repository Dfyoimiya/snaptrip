import request from '@/utils/request';

const BASE = '/admin/orders';

export const getOrderListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Order>>>(BASE, { params });

export const getOrderDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Order>>(`${BASE}/${id}`);

export const closeOrderAPI = (id: string, note?: string) =>
  request.post(`${BASE}/${id}/close`, null, { params: { note } });

export const deliveryOrderAPI = (id: string, data: API.OrderDelivery) =>
  request.post(`${BASE}/${id}/delivery`, data);

export const modifyOrderAddressAPI = (id: string, params: Record<string, string>) =>
  request.post(`${BASE}/${id}/modify-address`, null, { params });

export const modifyOrderPriceAPI = (id: string, data: API.OrderPriceModify) =>
  request.post(`${BASE}/${id}/modify-price`, data);

export const remarkOrderAPI = (id: string, note: string) =>
  request.post(`${BASE}/${id}/remark`, null, { params: { note } });

export const refundOrderAPI = (id: string, note?: string) =>
  request.post(`${BASE}/${id}/refund`, null, { params: { note } });

export const deleteOrderAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);
