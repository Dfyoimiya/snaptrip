/**
 * ============================================
 * 商品评价 API
 * ============================================
 */

import { get, post, put, del } from '@/utils/request'
import type { CommonPage } from '@/types/common'

// ── 类型 ──

export interface ReviewItem {
  id: string
  productId: string
  userId: string
  orderId?: string
  rating: number
  content?: string
  images?: string
  isAnonymous: boolean
  status: number
  reply?: string
  repliedAt?: string
  createdAt: string
  updatedAt: string
}

export interface ReviewCreateParams {
  product_id: string
  rating: number
  content?: string
  images?: string
  is_anonymous?: boolean
  order_id?: string
}

export interface ReviewUpdateParams {
  rating?: number
  content?: string
  images?: string
  is_anonymous?: boolean
}

// ── API ──

/** 创建评价 */
export const createReviewAPI = (data: ReviewCreateParams) => {
  return post<string>('/api/v1/portal/reviews', data)
}

/** 获取评价列表 */
export const listReviewsAPI = (params: {
  product_id?: string
  rating?: number
  page?: number
  page_size?: number
}) => {
  return get<CommonPage<ReviewItem>>('/api/v1/portal/reviews', params as Record<string, unknown>)
}

/** 获取评价详情 */
export const getReviewDetailAPI = (id: string) => {
  return get<ReviewItem>(`/api/v1/portal/reviews/${id}`)
}

/** 修改评价 */
export const updateReviewAPI = (id: string, data: ReviewUpdateParams) => {
  return put<ReviewItem>(`/api/v1/portal/reviews/${id}`, data)
}

/** 删除评价 */
export const deleteReviewAPI = (id: string) => {
  return del<null>(`/api/v1/portal/reviews/${id}`)
}
