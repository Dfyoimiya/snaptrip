import request from '@/utils/request'
import type { CommonResult } from '@/types/common'
import type { OmsOrderSetting } from '@/types/orderSetting'

export function getOrderSettingByIdAPI(id: string) {
  return request<CommonResult<OmsOrderSetting>>({
    url: '/admin/order-settings/' + id,
    method: 'get',
  })
}

export function orderSettingUpdateByIdAPI(id: string, data: OmsOrderSetting) {
  return request<CommonResult<OmsOrderSetting>>({
    url: '/admin/order-settings/' + id,
    method: 'put',
    data,
  })
}
