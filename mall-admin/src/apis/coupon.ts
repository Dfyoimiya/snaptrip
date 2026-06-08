import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsCoupon, SmsCouponExt, CouponQueryParam, CouponHistoryQueryParam } from '@/types/coupon'

/** 优惠券分页列表 —— GET /admin/coupons */
export function getCouponListAPI(params: CouponQueryParam) {
  return request<CommonResult<CommonPage<SmsCoupon>>>({
    url: '/admin/coupons',
    method: 'get',
    params: {
      keyword: params.name,
      type: params.type,
      page: params.page,
      page_size: params.page_size,
    },
  })
}

/** 创建优惠券 —— POST /admin/coupons */
export function createCouponAPI(data: SmsCouponExt) {
  return request<CommonResult<number>>({
    url: '/admin/coupons',
    method: 'post',
    data,
  })
}

/** 优惠券详情 —— GET /admin/coupons/{id} */
export function getCouponByIdAPI(id: number) {
  return request<CommonResult<SmsCouponExt>>({
    url: '/admin/coupons/' + id,
    method: 'get',
  })
}

/** 编辑优惠券 —— PUT /admin/coupons/{id} */
export function updateCouponByIdAPI(id: number, data: SmsCouponExt) {
  return request<CommonResult<number>>({
    url: '/admin/coupons/' + id,
    method: 'put',
    data,
  })
}

/** 删除优惠券 —— DELETE /admin/coupons/{id} */
export function deleteCouponByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/admin/coupons/' + id,
    method: 'delete',
  })
}

/** 优惠券领取/使用记录 —— GET /admin/coupons/{id}/histories */
export function getCouponHistoryListAPI(params: CouponHistoryQueryParam) {
  return request<CommonResult<CommonPage<never>>>({
    url: '/admin/coupons/' + params.couponId + '/histories',
    method: 'get',
    params: {
      page: params.page,
      page_size: params.page_size,
    },
  })
}
