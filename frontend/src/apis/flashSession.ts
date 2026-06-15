import type { CommonResult } from '@/types/common'
import type { SmsFlashPromotionSession } from '@/types/flash'
import request from '@/utils/request'

/** 可选场次列表 —— GET /admin/flash-promotions/{promoId}/sessions */
export function getFlashSessionSelectListAPI(params: { flashPromotionId: string }) {
  return request<CommonResult<SmsFlashPromotionSession[]>>({
    url: '/admin/flash-promotions/' + params.flashPromotionId + '/sessions',
    method: 'get',
  })
}

/** 所有场次列表 —— GET /admin/flash-promotions/sessions（带 promoId） */
export function getFlashSessionListAPI(params?: { promotionId?: string }) {
  const base = '/admin/flash-promotions'
  const promoPath = params?.promotionId ? '/' + params.promotionId : ''
  return request<CommonResult<SmsFlashPromotionSession[]>>({
    url: base + promoPath + '/sessions',
    method: 'get',
  })
}

/** 创建场次 —— POST /admin/flash-promotions/{promoId}/sessions */
export function flashSessionCreateAPI(data: SmsFlashPromotionSession & { promotionId?: string }) {
  const promoPath = data.promotionId ? '/' + data.promotionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoPath + '/sessions',
    method: 'post',
    data,
  })
}

/** 编辑场次 —— PUT /admin/flash-promotions/{promoId}/sessions/{id} */
export function flashSessionUpdateByIdAPI(id: string, data: SmsFlashPromotionSession & { promotionId?: string }) {
  const promoPath = data.promotionId ? '/' + data.promotionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoPath + '/sessions/' + id,
    method: 'put',
    data,
  })
}

/** 删除场次 —— DELETE /admin/flash-promotions/{promoId}/sessions/{id} */
export function flashSessionDeleteByIdAPI(id: string, params?: { promotionId?: string }) {
  const promoPath = params?.promotionId ? '/' + params.promotionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoPath + '/sessions/' + id,
    method: 'delete',
  })
}

/** 切换场次状态 —— PATCH /admin/flash-promotions/{promoId}/sessions/{id}/status */
export function flashSessionUpdateStatusByIdAPI(id: string, params: { status: number; promotionId?: string }) {
  const promoPath = params.promotionId ? '/' + params.promotionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoPath + '/sessions/' + id + '/status',
    method: 'patch',
    params: { status: params.status },
  })
}
