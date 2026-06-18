/**
 * ============================================
 * 品牌 API
 * 品牌详情、品牌商品列表等接口
 * ============================================
 */

import { get } from '@/utils/request'
import type { PmsBrand } from '@/types/brand'
import type { CommonPage } from '@/types/common'

/**
 * 获取品牌详情
 * @param id 品牌ID
 */
export const getBrandDetailAPI = (id: string) => {
  return get<PmsBrand>(`/api/v1/portal/brands/${id}`)
}

/**
 * 获取品牌商品列表 (使用商品搜索 + brand_id 过滤)
 * @param brandId 品牌ID
 * @param page 页码
 * @param pageSize 每页数量
 */
export const getBrandProductListAPI = (brandId: string, page = 1, pageSize = 10, sort = 0) => {
  const sortMap: Record<number, string> = { 0: 'default', 1: 'new', 2: 'sales', 3: 'price_asc', 4: 'price_desc' }
  return get<CommonPage<unknown>>('/api/v1/portal/products', {
    brand_id: brandId, page, page_size: pageSize, sort_by: sortMap[sort] || 'default',
  })
}

/**
 * 获取推荐品牌列表
 */
export const getBrandRecommendListAPI = (params?: { page?: number; page_size?: number }) => {
  return get<CommonPage<PmsBrand>>('/api/v1/portal/brands', params as Record<string, unknown>)
}
