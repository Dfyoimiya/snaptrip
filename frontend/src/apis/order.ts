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

/** 订单分页列表 —— GET /admin/orders */
export function getOrderListAPI(params: OrderQueryParam) {
  return request<CommonResult<CommonPage<OmsOrder>>>({
    url: '/admin/orders',
    method: 'get',
    params: {
      order_sn: params.orderSn,
      status: params.status,
      start_time: params.createdAt,
      page: params.page,
      page_size: params.page_size,
    },
  })
}

/** 关闭订单 —— POST /admin/orders/{id}/close?note=... */
export function orderUpdateCloseAPI(id: string, note: string) {
  return request<CommonResult<number>>({
    url: '/admin/orders/' + id + '/close',
    method: 'post',
    params: { note },
  })
}

/** 删除订单 —— DELETE /admin/orders/{id} */
export function orderDeleteByIdsAPI(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/orders/' + id,
    method: 'delete',
  })
}

/** 订单发货 —— POST /admin/orders/{id}/delivery */
export function orderUpdateDeliveryAPI(data: OmsOrderDeliveryParam[]) {
  // 批量发货需要逐个调用或后端提供批量接口
  return request<CommonResult<number>>({
    url: '/admin/orders/' + (data[0] as any)?.orderId + '/delivery',
    method: 'post',
    data: data[0],
  })
}

/** 订单详情 —— GET /admin/orders/{id} */
export function getOrderDetailByIdAPI(id: string) {
  return request<CommonResult<OmsOrderDetail>>({
    url: '/admin/orders/' + id,
    method: 'get',
  })
}

/** 修改收货地址 —— POST /admin/orders/{id}/modify-address */
export function orderUpdateReceiverInfoAPI(data: OmsReceiverInfoParam) {
  return request<CommonResult<number>>({
    url: '/admin/orders/' + (data as any)?.orderId + '/modify-address',
    method: 'post',
    params: {
      receiver_name: data.receiverName,
      receiver_phone: data.receiverPhone,
      receiver_detail_address: data.receiverDetailAddress,
    },
  })
}

/** 修改订单金额 —— POST /admin/orders/{id}/modify-price */
export function orderUpdateMoneyInfoAPI(data: OmsMoneyInfoParam) {
  return request<CommonResult<number>>({
    url: '/admin/orders/' + (data as any)?.orderId + '/modify-price',
    method: 'post',
    data,
  })
}

/** 添加备注 —— POST /admin/orders/{id}/remark?note=... */
export function orderUpdateNoteAPI(params: OmsOrderNoteParam) {
  return request<CommonResult<number>>({
    url: '/admin/orders/' + (params as any)?.orderId + '/remark',
    method: 'post',
    params: { note: (params as any)?.note },
  })
}
