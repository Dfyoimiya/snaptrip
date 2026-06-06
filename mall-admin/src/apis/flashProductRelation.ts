import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsFlashPromotionProductRelation, FlashProductQueryParam } from '@/types/flash'
import request from '@/utils/request'

export function getFlashProductRelationListAPI(params: FlashProductQueryParam) {
  return request<CommonResult<CommonPage<SmsFlashPromotionProductRelation>>>({
    url: '/flashProductRelation/list',
    method: 'get',
    params,
  })
}

export function flashProductRelationCreateAPI(data: SmsFlashPromotionProductRelation[]) {
  return request<CommonResult<number>>({
    url: '/flashProductRelation/create',
    method: 'post',
    data,
  })
}

export function flashProductRelationDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/flashProductRelation/delete/' + id,
    method: 'post',
  })
}

export function flashProductRelationUpdateByIdAPI(id: number, data: SmsFlashPromotionProductRelation) {
  return request<CommonResult<number>>({
    url: '/flashProductRelation/update/' + id,
    method: 'post',
    data,
  })
}
