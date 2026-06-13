/**
 * ============================================
 * 订单 API
 * 订单创建、查询、取消、确认收货等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type {
  ConfirmOrderResult,
  GenerateOrderResult,
  OrderParam,
  OmsOrderDetail,
  OmsOrderReturnApplyParam,
} from '@/types/order'
import type { CommonPage, PageParam } from '@/types/common'

/**
 * 生成确认单信息
 * @param cartIds 选中的购物车商品ID列表
 */
export const generateConfirmOrderAPI = (cartIds: number[]) => {
  return post<ConfirmOrderResult>('/order/generateConfirmOrder', cartIds)
}

/**
 * 生成订单
 * @param data 订单参数
 */
export const generateOrderAPI = (data: OrderParam) => {
  return post<GenerateOrderResult>('/order/generateOrder', data)
}

/**
 * 按状态分页获取用户订单列表
 * @param params 分页参数 + 状态
 */
export const getOrderListAPI = (params: PageParam & { status: number }) => {
  return get<CommonPage<OmsOrderDetail>>('/order/list', params as unknown as Record<string, unknown>)
}

/**
 * 根据ID获取订单详情
 * @param orderId 订单ID
 */
export const getOrderDetailAPI = (orderId: number) => {
  return get<OmsOrderDetail>(`/order/detail/${orderId}`)
}

/**
 * 用户取消订单
 * @param orderId 订单ID
 */
export const cancelUserOrderAPI = (orderId: number) => {
  return post<unknown>('/order/cancelUserOrder', null, { params: { orderId } })
}

/**
 * 用户确认收货
 * @param orderId 订单ID
 */
export const confirmReceiveOrderAPI = (orderId: number) => {
  return post<unknown>('/order/confirmReceiveOrder', null, { params: { orderId } })
}

/**
 * 用户删除订单
 * @param orderId 订单ID
 */
export const deleteOrderAPI = (orderId: number) => {
  return post<unknown>('/order/deleteOrder', null, { params: { orderId } })
}

/**
 * 支付成功回调
 * @param orderId 订单ID
 * @param payType 支付方式
 */
export const payOrderSuccessAPI = (orderId: number, payType: number) => {
  return post<unknown>('/order/paySuccess', null, { params: { orderId, payType } })
}

/**
 * 查询支付宝交易状态
 * @param outTradeNo 商户订单号
 */
export const fetchAlipayStatusAPI = (outTradeNo: string) => {
  return get<string>('/alipay/query', { outTradeNo })
}

/**
 * 申请退货
 * @param data 退货申请参数
 */
export const createReturnApplyAPI = (data: OmsOrderReturnApplyParam) => {
  return post<unknown>('/returnApply/create', data)
}
