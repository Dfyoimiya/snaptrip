import request from '@/utils/request'
import type { CommonResult } from '@/types/common'
import type { OmsOrderSetting } from '@/types/orderSetting'

export function getOrderSettingByIdAPI(id: number) {
  return request<CommonResult<OmsOrderSetting>>({
    url: '/orderSetting/' + id,
    method: 'get',
  })
}

export function orderSettingUpdateByIdAPI(id: number, data: OmsOrderSetting) {
  return request<CommonResult<number>>({
    url: '/orderSetting/update/' + id,
    method: 'post',
    data,
  })
}
