import request from '@/utils/request'
import type { CommonResult } from '@/types/common'
import type { OmsCompanyAddress } from '@/types/companyAddress'

export function getCompanyAddressListAPI() {
  return request<CommonResult<OmsCompanyAddress[]>>({
    url: '/companyAddress/list',
    method: 'get',
  })
}
