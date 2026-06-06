import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeNewProduct, NewProductQueryParam } from '@/types/newProduct'
import request from '@/utils/request'

export function getHomeNewProductListAPI(params: NewProductQueryParam) {
  return request<CommonResult<CommonPage<SmsHomeNewProduct>>>({
    url: '/home/newProduct/list',
    method: 'get',
    params,
  })
}

export function homeNewProductCreateAPI(data: SmsHomeNewProduct[]) {
  return request<CommonResult<number>>({
    url: '/home/newProduct/create',
    method: 'post',
    data,
  })
}

export function homeNewProductUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  return request<CommonResult<number>>({
    url: '/home/newProduct/update/recommendStatus',
    method: 'post',
    params,
  })
}

export function homeNewProductDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/home/newProduct/delete',
    method: 'post',
    params,
  })
}

export function homeNewProductUpdateSortByIdAPI(params: { id: number; sort: number }) {
  return request<CommonResult<number>>({
    url: '/home/newProduct/update/sort/' + params.id,
    method: 'post',
    params,
  })
}
