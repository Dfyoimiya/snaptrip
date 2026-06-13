/**
 * ============================================
 * 优惠券 API
 * 优惠券查询、领取、列表等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { SmsCoupon } from '@/types/coupon'

/**
 * 获取商品可用优惠券列表
 * @param productId 商品ID
 */
export const getProductCouponListAPI = (productId: number) => {
  return get<SmsCoupon[]>(`/member/coupon/listByProduct/${productId}`)
}

/**
 * 领取优惠券
 * @param couponId 优惠券ID
 */
export const addMemberCouponAPI = (couponId: number) => {
  return post<unknown>(`/member/coupon/add/${couponId}`)
}

/**
 * 获取我的优惠券列表
 * @param useStatus 使用状态：0->未使用；1->已使用；2->已过期
 */
export const getMemberCouponListAPI = (useStatus: number) => {
  return get<SmsCoupon[]>('/member/coupon/list', { useStatus })
}
