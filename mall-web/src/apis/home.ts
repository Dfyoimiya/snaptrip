/**
 * ============================================
 * 首页 API
 * 首页内容、推荐商品、分类等接口
 * ============================================
 */

import { get } from '@/utils/request'
import type { PmsProduct, PmsProductCategory } from '@/types/product'
import type { HomeContentResult } from '@/types/home'
import type { PageParam } from '@/types/common'

/** 首页内容 */
export const getHomeContentAPI = () => {
  return get<HomeContentResult>('/home/content')
}

/** 推荐商品列表 */
export const getRecommendProductListAPI = (params?: PageParam) => {
  return get<PmsProduct[]>('/home/recommendProductList', params as Record<string, unknown>)
}

/** 商品分类列表 */
export const getProductCateListAPI = (parentId: string | number) => {
  return get<PmsProductCategory[]>(`/home/productCateList/${parentId}`)
}

/** 新鲜好物列表 */
export const getNewProductListAPI = (params?: PageParam) => {
  return get<PmsProduct[]>('/home/newProductList', params as Record<string, unknown>)
}

/** 人气推荐列表 */
export const getHotProductListAPI = (params?: PageParam) => {
  return get<PmsProduct[]>('/home/hotProductList', params as Record<string, unknown>)
}
