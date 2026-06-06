import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsCoupon, SmsCouponExt, CouponQueryParam, CouponHistoryQueryParam } from '@/types/coupon'

export function getCouponListAPI(params: CouponQueryParam) {
  return request<CommonResult<CommonPage<SmsCoupon>>>({
    url: '/coupon/list',
    method: 'get',
    params,
  })
}

export function createCouponAPI(data: SmsCouponExt) {
  return request<CommonResult<number>>({
    url: '/coupon/create',
    method: 'post',
    data,
  })
}

export function getCouponByIdAPI(id: number) {
  return request<CommonResult<SmsCouponExt>>({
    url: '/coupon/' + id,
    method: 'get',
  })
}

export function updateCouponByIdAPI(id: number, data: SmsCouponExt) {
  return request<CommonResult<number>>({
    url: '/coupon/update/' + id,
    method: 'post',
    data,
  })
}

export function deleteCouponByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/coupon/delete/' + id,
    method: 'post',
  })
}

export function getCouponHistoryListAPI(params: CouponHistoryQueryParam) {
  return request<CommonResult<CommonPage<never>>>({
    url: '/couponHistory/list',
    method: 'get',
    params,
  })
}
