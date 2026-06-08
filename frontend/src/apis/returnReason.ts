import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { OmsOrderReturnReason } from '@/types/returnReason'
import type { PageParam } from '@/types/common'

export function getReturnReasonListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<OmsOrderReturnReason>>>({
    url: '/returnReason/list',
    method: 'get',
    params,
  })
}

export function returnReasonCreateAPI(data: OmsOrderReturnReason) {
  return request<CommonResult<number>>({
    url: '/returnReason/create',
    method: 'post',
    data,
  })
}

export function returnReasonUpdateAPI(id: number, data: OmsOrderReturnReason) {
  return request<CommonResult<number>>({
    url: '/returnReason/update/' + id,
    method: 'post',
    data,
  })
}

export function getReturnReasonByIdAPI(id: number) {
  return request<CommonResult<OmsOrderReturnReason>>({
    url: '/returnReason/' + id,
    method: 'get',
  })
}

export function returnReasonDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/returnReason/delete',
    method: 'post',
    params,
  })
}

export function returnReasonUpdateStatusAPI(params: { ids: string; status: number }) {
  return request<CommonResult<number>>({
    url: '/returnReason/update/status',
    method: 'post',
    params,
  })
}
