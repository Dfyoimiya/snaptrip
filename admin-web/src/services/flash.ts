import request from '@/utils/request';

const BASE = '/admin/flash-promotions';

// Flash promotions
export const getFlashPromotionListAPI = (params: Record<string, number>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.FlashPromotion>>>(BASE, { params });

export const createFlashPromotionAPI = (data: API.FlashPromotionCreate) =>
  request.post<API.ApiResponse<API.FlashPromotion>>(BASE, data);

export const updateFlashPromotionAPI = (id: string, data: Partial<API.FlashPromotionCreate & { status?: number }>) =>
  request.put<API.ApiResponse<API.FlashPromotion>>(`${BASE}/${id}`, data);

export const deleteFlashPromotionAPI = (id: string) =>
  request.delete(`${BASE}/${id}`);

// Flash sessions
export const getFlashSessionListAPI = (promoId: string) =>
  request.get<API.ApiResponse<API.FlashSession[]>>(`${BASE}/${promoId}/sessions`);

export const getAllSessionsAPI = (promotionId?: string) =>
  request.get<API.ApiResponse<API.FlashSession[]>>(`${BASE}/sessions`, { params: { promotionId } });

export const createFlashSessionAPI = (promoId: string, data: Omit<API.FlashSessionCreate, 'promotionId'>) =>
  request.post<API.ApiResponse<API.FlashSession>>(`${BASE}/${promoId}/sessions`, { ...data, promotion_id: promoId });

export const updateFlashSessionAPI = (promoId: string, sessionId: string, data: Partial<API.FlashSessionCreate>) =>
  request.put<API.ApiResponse<API.FlashSession>>(`${BASE}/${promoId}/sessions/${sessionId}`, data);

export const deleteFlashSessionAPI = (promoId: string, sessionId: string) =>
  request.delete(`${BASE}/${promoId}/sessions/${sessionId}`);

export const toggleFlashSessionStatusAPI = (promoId: string, sessionId: string, status: number) =>
  request.patch(`${BASE}/${promoId}/sessions/${sessionId}/status`, null, { params: { status } });

// Flash products
export const getFlashProductListAPI = (promoId: string, sessionId: string, params: Record<string, number>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.FlashProduct>>>(`${BASE}/${promoId}/sessions/${sessionId}/products`, { params });

export const createFlashProductAPI = (promoId: string, sessionId: string, data: API.FlashProductCreate) =>
  request.post<API.ApiResponse<API.FlashProduct>>(`${BASE}/${promoId}/sessions/${sessionId}/products`, { ...data, session_id: sessionId });

export const updateFlashProductAPI = (promoId: string, sessionId: string, productId: string, data: Partial<API.FlashProductCreate>) =>
  request.put<API.ApiResponse<API.FlashProduct>>(`${BASE}/${promoId}/sessions/${sessionId}/products/${productId}`, data);

export const deleteFlashProductAPI = (promoId: string, sessionId: string, productId: string) =>
  request.delete(`${BASE}/${promoId}/sessions/${sessionId}/products/${productId}`);
