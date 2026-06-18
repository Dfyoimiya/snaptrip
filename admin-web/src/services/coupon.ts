import request from '@/utils/request';

const BASE = '/admin/coupons';

export const getCouponListAPI = (params: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Coupon>>>(BASE, { params });

export const getCouponDetailAPI = (id: string) =>
  request.get<API.ApiResponse<API.Coupon>>(`${BASE}/${id}`);

export const createCouponAPI = (data: API.CouponCreate) =>
  request.post<API.ApiResponse<API.Coupon>>(BASE, data);

export const updateCouponAPI = (id: string, data: API.CouponUpdate) =>
  request.put<API.ApiResponse<API.Coupon>>(`${BASE}/${id}`, data);

export const deleteCouponAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

export const getCouponHistoryAPI = (id: string, params: Record<string, number>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.CouponHistory>>>(`${BASE}/${id}/histories`, { params });
