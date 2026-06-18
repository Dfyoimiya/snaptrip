import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsFlashPromotionProductRelation, FlashProductQueryParam } from '@/types/flash'
import request from '@/utils/request'

/** 秒杀商品列表 —— GET /admin/flash-promotions/{promoId}/sessions/{sessionId}/products */
export function getFlashProductRelationListAPI(
  params: FlashProductQueryParam & { promotionId?: string; sessionId?: string },
) {
  const promotionId = params.promotionId || params.flashPromotionId
  const sessionId = params.sessionId || params.flashPromotionSessionId
  const { flashPromotionId: _promotionId, flashPromotionSessionId: _sessionId, ...queryParams } = params
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
  const item = data[0]
  if (!item?.flashPromotionId || !item.flashPromotionSessionId) {
    return Promise.reject(new Error('请先选择秒杀活动和场次'))
  }
  return request<CommonResult<number>>({
    url:
      '/admin/flash-promotions/' +
      item.flashPromotionId +
      '/sessions/' +
      item.flashPromotionSessionId +
      '/products',
    method: 'post',
    data: item,
  })
}

/** 删除秒杀商品 —— DELETE /admin/flash-promotions/{promoId}/sessions/{sessionId}/products/{productId} */
export function flashProductRelationDeleteByIdAPI(
  id: string,
  params?: { promotionId?: string; sessionId?: string },
) {
  if (!params?.promotionId || !params.sessionId) {
    return Promise.reject(new Error('缺少秒杀活动或场次 ID'))
  }
  return request<CommonResult<number>>({
    url:
      '/admin/flash-promotions/' +
      params.promotionId +
      '/sessions/' +
      params.sessionId +
      '/products/' +
      id,
    method: 'delete',
  })
}

/** 编辑秒杀商品 —— PUT /admin/flash-promotions/{promoId}/sessions/{sessionId}/products/{id} */
export function flashProductRelationUpdateByIdAPI(
  id: string,
  data: SmsFlashPromotionProductRelation,
) {
  if (!data.flashPromotionId || !data.flashPromotionSessionId) {
    return Promise.reject(new Error('缺少秒杀活动或场次 ID'))
  }
  return request<CommonResult<number>>({
    url:
      '/admin/flash-promotions/' +
      data.flashPromotionId +
      '/sessions/' +
      data.flashPromotionSessionId +
      '/products/' +
      id,
    method: 'put',
    data,
  })
}
