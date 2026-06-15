/**
 * ============================================
 * 首页 API
 * 首页聚合、推荐商品、分类等接口
 * ============================================
 */

import { get } from '@/utils/request'
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
