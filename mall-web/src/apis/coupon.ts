/**
 * ============================================
 * 优惠券 API
 * 优惠券查询、领取、列表等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { SmsCoupon } from '@/types/coupon'
import type { CommonPage } from '@/types/common'

/**
 * 获取可领取优惠券列表
 */
export const getAvailableCouponsAPI = (page = 1, pageSize = 20) => {
  return get<CommonPage<SmsCoupon>>('/api/v1/portal/coupons/available', { page, page_size: pageSize })
}

/**
 * 领取优惠券
 * @param couponId 优惠券ID
 */
export const addMemberCouponAPI = (couponId: string) => {
  return post(`/api/v1/portal/coupons/${couponId}/claim`)
}

/**
 * 获取我的优惠券列表
 * @param useStatus 使用状态：0=未使用 1=已使用 2=已过期
 */
export const getMemberCouponListAPI = (useStatus?: number) => {
  return get<SmsCoupon[]>('/api/v1/portal/coupons/mine', { use_status: useStatus })
}

// 保留旧名兼容
export { getAvailableCouponsAPI as getProductCouponListAPI }
