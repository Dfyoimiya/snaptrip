import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsFlashPromotionProductRelation, FlashProductQueryParam } from '@/types/flash'
import request from '@/utils/request'

/** 秒杀商品列表 —— GET /admin/flash-promotions/{promoId}/sessions/{sessionId}/products */
export function getFlashProductRelationListAPI(params: FlashProductQueryParam & { promotionId?: number; sessionId?: number }) {
  const { promotionId, sessionId, ...queryParams } = params
  if (!promotionId || !sessionId) {
    return Promise.reject(new Error('请先选择秒杀活动和场次'))
  }
  return request<CommonResult<CommonPage<SmsFlashPromotionProductRelation>>>({
    url: '/admin/flash-promotions/' + promotionId + '/sessions/' + sessionId + '/products',
    method: 'get',
    params: queryParams,
  })
}

/** 添加秒杀商品 —— POST /admin/flash-promotions/{promoId}/sessions/{sessionId}/products */
export function flashProductRelationCreateAPI(data: SmsFlashPromotionProductRelation[]) {
  const item = data[0] as any
  const promoId = item?.promotionId ? '/' + item.promotionId : ''
  const sessionId = item?.sessionId ? '/' + item.sessionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoId + '/sessions' + sessionId + '/products',
    method: 'post',
    data: item,
  })
}

/** 删除秒杀商品 —— DELETE /admin/flash-promotions/{promoId}/sessions/{sessionId}/products/{productId} */
export function flashProductRelationDeleteByIdAPI(id: string, params?: { promotionId?: number; sessionId?: number }) {
  const promoId = params?.promotionId ? '/' + params.promotionId : ''
  const sessionId = params?.sessionId ? '/' + params.sessionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoId + '/sessions' + sessionId + '/products/' + id,
    method: 'delete',
  })
}

/** 编辑秒杀商品 —— PUT /admin/flash-promotions/{promoId}/sessions/{sessionId}/products/{id} */
export function flashProductRelationUpdateByIdAPI(id: string, data: SmsFlashPromotionProductRelation & { promotionId?: number; sessionId?: number }) {
  const promoId = data.promotionId ? '/' + data.promotionId : ''
  const sessionId = data.sessionId ? '/' + data.sessionId : ''
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions' + promoId + '/sessions' + sessionId + '/products/' + id,
    method: 'put',
    data,
  })
}
