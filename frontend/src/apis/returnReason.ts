import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { OmsOrderReturnReason } from '@/types/returnReason'
import type { PageParam } from '@/types/common'

export function getReturnReasonListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<OmsOrderReturnReason>>>({
    url: '/admin/return-reasons',
    method: 'get',
    params,
  })
}

export function returnReasonCreateAPI(data: OmsOrderReturnReason) {
  return request<CommonResult<OmsOrderReturnReason>>({
    url: '/admin/return-reasons',
    method: 'post',
    data,
  })
}

export function returnReasonUpdateAPI(id: string, data: OmsOrderReturnReason) {
  return request<CommonResult<OmsOrderReturnReason>>({
    url: '/admin/return-reasons/' + id,
    method: 'put',
    data,
  })
}

export function returnReasonDeleteByIdsAPI(ids: string[]) {
  const query = ids.map(id => `ids=${encodeURIComponent(id)}`).join('&')
  return request<CommonResult<null>>({
    url: `/admin/return-reasons?${query}`,
    method: 'delete',
  })
}

export function returnReasonUpdateStatusAPI(ids: string[], status: number) {
  const query = ids.map(id => `ids=${encodeURIComponent(id)}`).join('&')
  return request<CommonResult<null>>({
    url: `/admin/return-reasons/status?${query}&status=${status}`,
    method: 'patch',
  })
}
