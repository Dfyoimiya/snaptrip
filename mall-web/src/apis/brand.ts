/**
 * ============================================
 * 品牌 API
 * 品牌详情、品牌商品列表等接口
 * ============================================
 */

import { get } from '@/utils/request'
import type { PmsBrand } from '@/types/brand'
import type { PmsProduct } from '@/types/product'
import type { CommonPage, PageParam } from '@/types/common'

/**
 * 获取品牌详情
 * @param id 品牌ID
 */
export const getBrandDetailAPI = (id: number) => {
  return get<PmsBrand>(`/brand/detail/${id}`)
}

/**
 * 获取品牌商品列表
 * @param brandId 品牌ID
 * @param pageNum 页码
 * @param pageSize 每页数量
 */
export const getBrandProductListAPI = (brandId: number, pageNum = 1, pageSize = 10) => {
  return get<CommonPage<PmsProduct>>('/brand/productList', { brandId, pageNum, pageSize })
}

/**
 * 获取推荐品牌列表
 * @param params 分页参数
 */
export const getBrandRecommendListAPI = (params?: PageParam) => {
  return get<PmsBrand[]>('/brand/recommendList', params as unknown as Record<string, unknown>)
}
