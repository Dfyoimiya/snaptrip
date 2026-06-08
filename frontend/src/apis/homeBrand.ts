import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeBrand } from '@/types/homeBrand'
import request from '@/utils/request'

export function getHomeBrandListAPI(params: { pageNum: number; pageSize: number; brandName?: string; recommendStatus?: number }) {
  return request<CommonResult<CommonPage<SmsHomeBrand>>>({
    url: '/home/brand/list',
    method: 'get',
    params,
  })
}

export function homeBrandCreateAPI(data: SmsHomeBrand[]) {
  return request<CommonResult<number>>({
    url: '/home/brand/create',
    method: 'post',
    data,
  })
}

export function homeBrandUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  return request<CommonResult<number>>({
    url: '/home/brand/update/recommendStatus',
    method: 'post',
    params,
  })
}

export function homeBrandDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/home/brand/delete',
    method: 'post',
    params,
  })
}

export function homeBrandUpdateSortAPI(params: { id: number; sort: number }) {
  return request<CommonResult<number>>({
    url: '/home/brand/update/sort/' + params.id,
    method: 'post',
    params,
  })
}

// 向后兼容别名（视图层使用）
export const fetchHomeBrandList = getHomeBrandListAPI
export const addHomeBrand = homeBrandCreateAPI
export const deleteHomeBrand = homeBrandDeleteByIdsAPI
export const updateHomeBrandSort = homeBrandUpdateSortAPI
export const updateHomeBrandStatus = homeBrandUpdateRecommendStatusAPI
export const batchDeleteHomeBrand = homeBrandDeleteByIdsAPI
