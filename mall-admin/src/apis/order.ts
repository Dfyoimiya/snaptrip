import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type {
  OmsOrder,
  OmsOrderDetail,
  OmsOrderDeliveryParam,
  OmsReceiverInfoParam,
  OmsMoneyInfoParam,
  OmsOrderNoteParam,
  OrderQueryParam,
} from '@/types/order'

export function getOrderListAPI(params: OrderQueryParam) {
  return request<CommonResult<CommonPage<OmsOrder>>>({
    url: '/order/list',
    method: 'get',
    params,
  })
}

export function orderUpdateCloseAPI(params: { ids: string; note: string }) {
  return request<CommonResult<number>>({
    url: '/order/update/close',
    method: 'post',
    params,
  })
}

export function orderDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/order/delete',
    method: 'post',
    params,
  })
}

export function orderUpdateDeliveryAPI(data: OmsOrderDeliveryParam[]) {
  return request<CommonResult<number>>({
    url: '/order/update/delivery',
    method: 'post',
    data,
  })
}

export function getOrderDetailByIdAPI(id: number) {
  return request<CommonResult<OmsOrderDetail>>({
    url: '/order/' + id,
    method: 'get',
  })
}

export function orderUpdateReceiverInfoAPI(data: OmsReceiverInfoParam) {
  return request<CommonResult<number>>({
    url: '/order/update/receiverInfo',
    method: 'post',
    data,
  })
}

export function orderUpdateMoneyInfoAPI(data: OmsMoneyInfoParam) {
  return request<CommonResult<number>>({
    url: '/order/update/moneyInfo',
    method: 'post',
    data,
  })
}

export function orderUpdateNoteAPI(params: OmsOrderNoteParam) {
  return request<CommonResult<number>>({
    url: '/order/update/note',
    method: 'post',
    params,
  })
}
