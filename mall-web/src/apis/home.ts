/**
 * ============================================
 * 首页 API
 * 首页聚合、推荐商品、分类、个性化推荐等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { PmsProductCategory } from '@/types/product'
import type { HomeContentResult } from '@/types/home'

/** 首页聚合内容 */
export const getHomeContentAPI = () => {
  return get<HomeContentResult>('/api/v1/portal/home')
}

/** 首页推荐商品 = 按销量排序 */
export const getRecommendProductListAPI = (params?: { page?: number; page_size?: number }) => {
  return get<{ items: unknown[] }>('/api/v1/portal/products', {
    sort_by: 'sales',
    page: params?.page || 1,
    page_size: params?.page_size || 8,
  })
}

/** 商品分类列表 — 一级分类 */
export const getProductCateListAPI = (parentId: number | string) => {
  return get<PmsProductCategory[]>(`/api/v1/portal/categories`, { parent_id: parentId })
}

/** 新品推荐 = 按上架时间排序 */
export const getNewProductListAPI = (params?: { page?: number; page_size?: number }) => {
  return get<{ items: unknown[] }>('/api/v1/portal/products', {
    sort_by: 'new',
    page: params?.page || 1,
    page_size: params?.page_size || 8,
  })
}

/** 人气推荐 = 按销量排序 (同推荐) */
export const getHotProductListAPI = (params?: { page?: number; page_size?: number }) => {
  return get<{ items: unknown[] }>('/api/v1/portal/products', {
    sort_by: 'sales',
    page: params?.page || 1,
    page_size: params?.page_size || 8,
  })
}

// ── 个性化推荐 ──

export interface RecommendationProduct {
  productId: string
  name: string
  categoryId: string
  price: number
  brandName: string
  imageUrl: string
  saleCount: number
  stock: number
  score: number
  marketingCopy: string
}

export interface RecommendationResponse {
  requestId: string
  userId: string | null
  products: RecommendationProduct[]
  copies: { productId: string; copy: string }[]
  experimentGroup: string
  totalLatencyMs: number
}

/** 个性化推荐 — POST /portal/recommendations (LLM 耗时较长, 30s 超时) */
export const getPersonalizedRecommendationsAPI = (params: {
  scene?: string
  numItems?: number
  productId?: string
}) => {
  return post<RecommendationResponse>('/api/v1/portal/recommendations', {
    scene: params.scene || 'homepage',
    num_items: params.numItems || 10,
    product_id: params.productId || null,
  }, { timeout: 30000 })
}

/** 首页快捷推荐 — GET /portal/recommendations/home */
export const getHomeRecommendationsAPI = (limit: number = 10) => {
  return get<RecommendationResponse>('/api/v1/portal/recommendations/home', { limit })
}

// ── 多维度首页推荐 Feed ──

export interface FeedProduct {
  productId: string
  name: string
  price: number
  imageUrl: string
  brandName: string
  categoryId: string
  saleCount: number
  stock: number
  score: number
  marketingCopy: string
  promotionPrice: number | null
  promotionType: number
  newStatus: number
  recommendStatus: number
}

export interface SearchDiscoveryItem {
  query: string
  count: number
}

export interface FeedSection {
  sectionType: 'guess_you_like' | 'trending_now' | 'new_arrivals' | 'recently_viewed' | 'search_discovery'
  title: string
  subTitle: string
  products: FeedProduct[]
  suggestions: SearchDiscoveryItem[]
}

export interface HomeFeedResponse {
  sections: FeedSection[]
  userId: string | null
  sessionId: string | null
}

/** 首页多维度推荐 Feed */
export const getHomeFeedAPI = (limit: number = 10) => {
  return get<HomeFeedResponse>('/api/v1/portal/home/feed', { limit })
}
