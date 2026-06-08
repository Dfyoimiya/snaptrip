import type { CommonResult } from '@/types/common'
import type { OssPolicyResult } from '@/types/oss'
import request from '@/utils/request'

export function ossPolicyAPI() {
  return request<CommonResult<OssPolicyResult>>({
    url: '/aliyun/oss/policy',
    method: 'get',
  })
}
