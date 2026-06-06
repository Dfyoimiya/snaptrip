import type { CommonResult } from '@/types/common'
import type { SmsFlashPromotionSession } from '@/types/flash'
import request from '@/utils/request'

export function getFlashSessionSelectListAPI(params: { flashPromotionId: number }) {
  return request<CommonResult<SmsFlashPromotionSession[]>>({
    url: '/flashSession/selectList',
    method: 'get',
    params,
  })
}

export function getFlashSessionListAPI() {
  return request<CommonResult<SmsFlashPromotionSession[]>>({
    url: '/flashSession/list',
    method: 'get',
  })
}

export function flashSessionCreateAPI(data: SmsFlashPromotionSession) {
  return request<CommonResult<number>>({
    url: '/flashSession/create',
    method: 'post',
    data,
  })
}

export function flashSessionUpdateByIdAPI(id: number, data: SmsFlashPromotionSession) {
  return request<CommonResult<number>>({
    url: '/flashSession/update/' + id,
    method: 'post',
    data,
  })
}

export function flashSessionDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/flashSession/delete/' + id,
    method: 'post',
  })
}

export function flashSessionUpdateStatusByIdAPI(id: number, params: { status: number }) {
  return request<CommonResult<number>>({
    url: '/flashSession/update/status/' + id,
    method: 'post',
    params,
  })
}
