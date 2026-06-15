/**
 * ============================================
 * 订单 API
 * 订单创建、查询、取消、确认收货等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { OmsOrderDetail, OrderParam, GenerateOrderResult } from '@/types/order'
import type { CommonPage } from '@/types/common'

/**
 * 创建订单（从购物车结算）
 * @param data 订单参数
 */
export const generateOrderAPI = (data: OrderParam) => {
  return post<GenerateOrderResult>('/api/v1/portal/orders', data)
}

/**
 * 按状态分页获取用户订单列表
 * @param params 分页参数 + 状态
 */
export const getOrderListAPI = (params: { status?: number; page?: number; page_size?: number }) => {
  return get<CommonPage<OmsOrderDetail>>('/api/v1/portal/orders', params as Record<string, unknown>)
}

/**
 * 根据ID获取订单详情
 * @param orderId 订单ID
 */
export const getOrderDetailAPI = (orderId: string) => {
  return get<OmsOrderDetail>(`/api/v1/portal/orders/${orderId}`)
}

/**
 * 用户取消订单
 * @param orderId 订单ID
 */
export const cancelUserOrderAPI = (orderId: string) => {
  return post(`/api/v1/portal/orders/${orderId}/cancel`)
}

/**
 * 用户确认收货
 * @param orderId 订单ID
 */
export const confirmReceiveOrderAPI = (orderId: string) => {
  return post(`/api/v1/portal/orders/${orderId}/confirm-receipt`)
}

/**
 * 支付订单
 * @param orderId 订单ID
 */
export const payOrderAPI = (orderId: string) => {
  return post(`/api/v1/portal/orders/${orderId}/pay`)
}

// 保留旧名兼容
export const payOrderSuccessAPI = payOrderAPI

/**
 * 查询支付宝交易状态 (mock — always returns success)
 */
export const fetchAlipayStatusAPI = async (_outTradeNo: string): Promise<string> => {
  return 'TRADE_SUCCESS'
}
