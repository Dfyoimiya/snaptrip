import type { CommonResult } from '@/types/common'
import type { UmsMemberLevel } from '@/types/memberLevel'
import request from '@/utils/request'

export function getMemberLevelListAPI(params: { defaultStatus: number }) {
  return request<CommonResult<UmsMemberLevel[]>>({
    url: '/memberLevel/list',
    method: 'get',
    params,
  })
}
