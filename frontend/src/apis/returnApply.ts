import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { OmsOrderReturnApply, ReturnApplyQueryParam, OmsUpdateStatusParam } from '@/types/returnApply'

export function getReturnApplyListAPI(params: ReturnApplyQueryParam) {
  return request<CommonResult<CommonPage<OmsOrderReturnApply>>>({
    url: '/returnApply/list',
    method: 'get',
    params,
  })
}

export function getReturnApplyByIdAPI(id: number) {
  return request<CommonResult<OmsOrderReturnApply>>({
    url: '/returnApply/' + id,
    method: 'get',
  })
}

export function returnApplyUpdateStatusAPI(id: number, data: OmsUpdateStatusParam) {
  return request<CommonResult<number>>({
    url: '/returnApply/update/status/' + id,
    method: 'post',
    data,
  })
}

export function returnApplyDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/returnApply/delete',
    method: 'post',
    params,
  })
}
