/**
 * ============================================
 * 会员商品收藏 API
 * 对应原项目 apis/memberProductCollection.ts
 * ============================================
 */

import request from '@/utils/request'
import type { MemberProductCollection } from '@/types/memberProductCollection'
import type { CommonPage } from '@/types/common'

/** 创建商品收藏 */
export const createProductCollectionAPI = (data: MemberProductCollection) => {
  return request({
    method: 'POST',
    url: '/member/productCollection/add',
    data,
  })
}

/** 删除商品收藏 */
export const deleteProductCollectionAPI = (params: { productId: number }) => {
  return request({
    method: 'POST',
    url: '/member/productCollection/delete',
    params,
  })
}

/** 获取商品收藏列表 */
export const fetchProductCollectionListAPI = (params: { pageNum: number; pageSize: number }) => {
  return request<CommonPage<MemberProductCollection>>({
    method: 'GET',
    url: '/member/productCollection/list',
    params,
  })
}

/** 查询商品收藏详情 */
export const getProductCollectionDetailAPI = (params: { productId: number }) => {
  return request<MemberProductCollection>({
    method: 'GET',
    url: '/member/productCollection/detail',
    params,
  })
}

/** 清空商品收藏 */
export const clearProductCollectionAPI = () => {
  return request({
    method: 'POST',
    url: '/member/productCollection/clear',
  })
}
