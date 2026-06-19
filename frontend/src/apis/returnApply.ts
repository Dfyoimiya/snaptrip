import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { OmsOrderReturnApply, ReturnApplyQueryParam, ReturnApplyUpdateStatusParam } from '@/types/returnApply'

export function getReturnApplyListAPI(params: ReturnApplyQueryParam) {
  return request<CommonResult<CommonPage<OmsOrderReturnApply>>>({
    url: '/admin/return-applies',
    method: 'get',
    params,
  })
}

export function getReturnApplyDetailAPI(id: string) {
  return request<CommonResult<OmsOrderReturnApply>>({
    url: `/admin/return-applies/${id}`,
    method: 'get',
  })
}

export function updateReturnApplyStatusAPI(id: string, data: ReturnApplyUpdateStatusParam) {
  return request<CommonResult<OmsOrderReturnApply>>({
    url: `/admin/return-applies/${id}/status`,
    method: 'patch',
    data,
  })
}

export function returnApplyDeleteByIdsAPI(ids: string[]) {
  const query = ids.map(id => `ids=${encodeURIComponent(id)}`).join('&')
  return request<CommonResult<null>>({
    url: `/admin/return-applies?${query}`,
    method: 'delete',
  })
}
