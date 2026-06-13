/**
 * ============================================
 * 商品 API
 * 商品详情、搜索、分类等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type {
  PmsProduct,
  PmsPortalProductDetail,
  ProductListParam,
  CategoryTreeNode,
} from '@/types/product'
import type { CommonPage } from '@/types/common'

/**
 * 根据ID获取商品详情
 * @param id 商品ID
 */
export const getProductDetailAPI = (id: number) => {
  return get<PmsPortalProductDetail>(`/product/detail/${id}`)
}

/**
 * 分页搜索商品列表
 * @param params 搜索参数
 */
export const searchProductListAPI = (params: ProductListParam) => {
  return get<CommonPage<PmsProduct>>('/product/search', params as unknown as Record<string, unknown>)
}

/**
 * 获取商品分类树
 */
export const getCategoryTreeAPI = () => {
  return get<CategoryTreeNode[]>('/product/categoryTreeList')
}

/**
 * 获取分类下的商品列表
 * @param categoryId 分类ID
 * @param pageNum 页码
 * @param pageSize 每页数量
 */
export const getProductsByCategoryAPI = (
  categoryId: number,
  pageNum = 1,
  pageSize = 10,
) => {
  return get<CommonPage<PmsProduct>>(`/product/list/${categoryId}`, {
    pageNum,
    pageSize,
  })
}

/**
 * 添加商品浏览记录
 * @param productId 商品ID
 */
export const addProductViewHistoryAPI = (productId: number) => {
  return post<unknown>('/product/view', { productId })
}
