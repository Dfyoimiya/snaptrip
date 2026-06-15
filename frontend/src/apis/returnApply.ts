import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { OmsOrderReturnApply, ReturnApplyQueryParam } from '@/types/returnApply'

export function getReturnApplyListAPI(params: ReturnApplyQueryParam) {
  return request<CommonResult<CommonPage<OmsOrderReturnApply>>>({
    url: '/admin/return-applies',
    method: 'get',
    params,
  })
}

export function returnApplyDeleteByIdsAPI(ids: string[]) {
  const query = ids.map(id => `ids=${encodeURIComponent(id)}`).join('&')
  return request<CommonResult<null>>({
    url: `/admin/return-applies?${query}`,
    method: 'delete',
  })
}
