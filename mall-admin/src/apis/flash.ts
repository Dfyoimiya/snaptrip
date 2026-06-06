import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import type { SmsFlashPromotion } from '@/types/flash'
import request from '@/utils/request'

export function getFlashListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<SmsFlashPromotion>>>({
    url: '/flash/list',
    method: 'get',
    params,
  })
}

export function flashCreateAPI(data: SmsFlashPromotion) {
  return request<CommonResult<number>>({
    url: '/flash/create',
    method: 'post',
    data,
  })
}

export function flashUpdateByIdAPI(id: number, data: SmsFlashPromotion) {
  return request<CommonResult<number>>({
    url: '/flash/update/' + id,
    method: 'post',
    data,
  })
}

export function flashDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/flash/delete/' + id,
    method: 'post',
  })
}

export function flashUpdateStatusByIdAPI(id: number, params: { status: number }) {
  return request<CommonResult<number>>({
    url: '/flash/update/status/' + id,
    method: 'post',
    params,
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
