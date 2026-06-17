/**
 * ============================================
 * 商品 API
 * 商品详情、搜索、分类等接口
 * ============================================
 */

import { get } from '@/utils/request'
import type {
  PmsPortalProductDetail,
  ProductListParam,
  CategoryTreeNode,
} from '@/types/product'
import type { CommonPage } from '@/types/common'

/**
 * 根据ID获取商品详情
 * @param id 商品ID (UUID)
 */
export const getProductDetailAPI = (id: string) => {
  return get<PmsPortalProductDetail>(`/api/v1/portal/products/${id}`)
}

/**
 * 分页搜索商品列表
 * @param params 搜索参数
 */
export const searchProductListAPI = (params: ProductListParam) => {
  return get<CommonPage<unknown>>('/api/v1/portal/products', {
    keyword: params.keyword,
    category_id: params.productCategoryId,
    brand_id: params.brandId,
    min_price: params.minPrice,
    max_price: params.maxPrice,
    sort_by: _mapSort(params.sort),
    page: (params as unknown as Record<string, unknown>).pageNum || 1,
    page_size: (params as unknown as Record<string, unknown>).pageSize || 20,
  })
}

/** 前端排序值 → 后端 sort_by 参数 */
function _mapSort(sort: number): string {
  const map: Record<number, string> = { 0: 'default', 1: 'new', 2: 'sales', 3: 'price_asc', 4: 'price_desc' }
  return map[sort] || 'default'
}

/**
 * 获取商品分类树
 */
export const getCategoryTreeAPI = () => {
  return get<CategoryTreeNode[]>('/api/v1/portal/categories/tree')
}

/**
 * 获取分类下的商品列表
 * @param categoryId 分类ID
 * @param page 页码
 * @param pageSize 每页数量
 */
export const getProductsByCategoryAPI = (
  categoryId: string,
  page = 1,
  pageSize = 10,
) => {
  return get<CommonPage<unknown>>(`/api/v1/portal/products/category/${categoryId}`, {
    page,
    page_size: pageSize,
  })
}
