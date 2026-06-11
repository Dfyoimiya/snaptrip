/**
 * ============================================
 * 会员品牌关注 API
 * 对应原项目 apis/memberBrandAttention.ts
 * ============================================
 */

import request from '@/utils/request'
import type { MemberBrandAttention } from '@/types/memberBrandAttention'
import type { CommonPage } from '@/types/common'

/** 添加品牌关注 */
export const createBrandAttentionAPI = (data: MemberBrandAttention) => {
  return request({
    method: 'POST',
    url: '/member/attention/add',
    data,
  })
}

/** 取消品牌关注 */
export const deleteBrandAttentionAPI = (brandId: number) => {
  return request({
    method: 'POST',
    url: '/member/attention/delete',
    params: { brandId },
  })
}

/** 获取品牌关注列表 */
export const fetchBrandAttentionListAPI = (params?: { pageNum?: number; pageSize?: number }) => {
  return request<CommonPage<MemberBrandAttention>>({
    method: 'GET',
    url: '/member/attention/list',
    params,
  })
}

/** 获取品牌关注详情 */
export const getBrandAttentionDetailAPI = (brandId: number) => {
  return request<MemberBrandAttention>({
    method: 'GET',
    url: '/member/attention/detail',
    params: { brandId },
  })
}

/** 清空品牌关注 */
export const clearBrandAttentionAPI = () => {
  return request({
    method: 'POST',
    url: '/member/attention/clear',
  })
}
