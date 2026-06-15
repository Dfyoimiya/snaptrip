/**
 * ============================================
 * 会员商品收藏 API — 映射到后端 favorites
 * ============================================
 */

import { get, post, del } from '@/utils/request'
import type { CommonPage } from '@/types/common'

/** 添加商品收藏 → POST /api/v1/portal/member/favorites?product_id= */
export const createProductCollectionAPI = (data: { productId: string }) => {
  return post(`/api/v1/portal/member/favorites?product_id=${data.productId}`)
}

/** 取消商品收藏 → DELETE /api/v1/portal/member/favorites/{product_id} */
export const deleteProductCollectionAPI = (params: { productId: string }) => {
  return del(`/api/v1/portal/member/favorites/${params.productId}`)
}

/** 获取商品收藏列表 → GET /api/v1/portal/member/favorites */
export const fetchProductCollectionListAPI = (params: { pageNum: number; pageSize: number }) => {
  return get<CommonPage<unknown>>('/api/v1/portal/member/favorites', {
    page: params.pageNum,
    page_size: params.pageSize,
  })
}

/** 查询商品收藏详情 — 后端无此接口，返回 null */
export const getProductCollectionDetailAPI = async (_params: { productId: string }) => {
  return null
}

/** 清空商品收藏 — 后端无批量删除接口 */
export const clearProductCollectionAPI = async () => {
  console.warn('[API] 清空收藏功能暂未实现')
}
