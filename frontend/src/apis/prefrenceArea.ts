import type { CommonResult } from '@/types/common'
import type { CmsPrefrenceArea } from '@/types/prefrenceArea'
import request from '@/utils/request'

export function getPrefrenceAreaListAllAPI() {
  return request<CommonResult<CmsPrefrenceArea[]>>({
    url: '/prefrenceArea/listAll',
    method: 'get',
  })
}
