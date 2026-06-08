import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeRecommendSubject, HomeSubjectQueryParam } from '@/types/homeSubject'
import request from '@/utils/request'

export function getHomeRecommendSubjectListAPI(params: HomeSubjectQueryParam) {
  return request<CommonResult<CommonPage<SmsHomeRecommendSubject>>>({
    url: '/home/recommendSubject/list',
    method: 'get',
    params,
  })
}

export function homeRecommendSubjectCreateAPI(data: SmsHomeRecommendSubject[]) {
  return request<CommonResult<number>>({
    url: '/home/recommendSubject/create',
    method: 'post',
    data,
  })
}

export function homeRecommendSubjectUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  return request<CommonResult<number>>({
    url: '/home/recommendSubject/update/recommendStatus',
    method: 'post',
    params,
  })
}

export function homeRecommendSubjectDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/home/recommendSubject/delete',
    method: 'post',
    params,
  })
}

export function homeRecommendSubjectUpdateSortAPI(params: { id: number; sort: number }) {
  return request<CommonResult<number>>({
    url: '/home/recommendSubject/update/sort/' + params.id,
    method: 'post',
    params,
  })
}
