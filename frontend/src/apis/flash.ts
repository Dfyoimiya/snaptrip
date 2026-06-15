import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import type { SmsFlashPromotion } from '@/types/flash'
import request from '@/utils/request'

/** 秒杀活动列表 —— GET /admin/flash-promotions */
export function getFlashListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<SmsFlashPromotion>>>({
    url: '/admin/flash-promotions',
    method: 'get',
    params,
  })
}

/** 创建秒杀活动 —— POST /admin/flash-promotions */
export function flashCreateAPI(data: SmsFlashPromotion) {
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions',
    method: 'post',
    data,
  })
}

/** 编辑秒杀活动 —— PUT /admin/flash-promotions/{id} */
export function flashUpdateByIdAPI(id: string, data: SmsFlashPromotion) {
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions/' + id,
    method: 'put',
    data,
  })
}

/** 删除秒杀活动 —— DELETE /admin/flash-promotions/{id} */
export function flashDeleteByIdAPI(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions/' + id,
    method: 'delete',
  })
}

/** 切换活动状态 —— PUT /admin/flash-promotions/{id} (body: {status}) */
export function flashUpdateStatusByIdAPI(id: string, params: { status: number }) {
  return request<CommonResult<number>>({
    url: '/admin/flash-promotions/' + id,
    method: 'put',
    data: { status: params.status },
  })
}

// 向后兼容别名（视图层使用）
export const fetchFlashPromotionList = getFlashListAPI
export const saveFlashPromotion = flashCreateAPI
export const deleteFlashPromotion = flashDeleteByIdAPI
export const updateFlashPromotionStatus = flashUpdateStatusByIdAPI

// 重新导出 flashSession 和 flashProductRelation
export {
  getFlashSessionSelectListAPI,
  getFlashSessionListAPI,
  flashSessionCreateAPI,
  flashSessionUpdateByIdAPI,
  flashSessionDeleteByIdAPI,
  flashSessionUpdateStatusByIdAPI,
  getFlashSessionListAPI as fetchSessionList,
  flashSessionCreateAPI as saveSession,
  flashSessionDeleteByIdAPI as deleteSession,
  flashSessionUpdateStatusByIdAPI as updateSessionStatus,
} from './flashSession'
export {
  getFlashProductRelationListAPI,
  flashProductRelationCreateAPI,
  flashProductRelationDeleteByIdAPI,
  flashProductRelationUpdateByIdAPI,
  getFlashProductRelationListAPI as fetchFlashProductList,
  flashProductRelationCreateAPI as saveFlashProduct,
  flashProductRelationDeleteByIdAPI as deleteFlashProduct,
} from './flashProductRelation'
