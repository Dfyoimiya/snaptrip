import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeRecommendProduct, RecommendProductQueryParam } from '@/types/recommendProduct'
import request from '@/utils/request'

export function getHomeRecommendProductListAPI(params: RecommendProductQueryParam) {
  return request<CommonResult<CommonPage<SmsHomeRecommendProduct>>>({
    url: '/home/recommendProduct/list',
    method: 'get',
    params,
  })
}

export function homeRecommendProductCreateAPI(data: SmsHomeRecommendProduct[]) {
  return request<CommonResult<number>>({
    url: '/home/recommendProduct/create',
    method: 'post',
    data,
  })
}

export function homeRecommendProductUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  return request<CommonResult<number>>({
    url: '/home/recommendProduct/update/recommendStatus',
    method: 'post',
    params,
  })
}

export function homeRecommendProductDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/home/recommendProduct/delete',
    method: 'post',
    params,
  })
}

export function homeRecommendProductUpdateSortByIdAPI(params: { id: number; sort: number }) {
  return request<CommonResult<number>>({
    url: '/home/recommendProduct/update/sort/' + params.id,
    method: 'post',
    params,
  })
}
