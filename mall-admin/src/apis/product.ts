import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProduct, ProductQueryParam, PmsProductParam } from '@/types/product'
import request from '@/utils/request'

export function getProductListAPI(params: ProductQueryParam) {
  return request<CommonResult<CommonPage<PmsProduct>>>({
    url: '/product/list',
    method: 'get',
    params,
  })
}

export function createProductAPI(data: PmsProductParam) {
  return request<CommonResult<number>>({
    url: '/product/create',
    method: 'post',
    data,
  })
}

export function updateProductAPI(id: number, data: PmsProductParam) {
  return request<CommonResult<number>>({
    url: '/product/update/' + id,
    method: 'post',
    data,
  })
}

export function getProductAPI(id: number) {
  return request<CommonResult<PmsProductParam>>({
    url: '/product/updateInfo/' + id,
    method: 'get',
  })
}

export function productUpdateDeleteStatusAPI(params: { ids: string; deleteStatus: number }) {
  return request<CommonResult<number>>({
    url: '/product/update/deleteStatus',
    method: 'post',
    params,
  })
}

export function productUpdateNewStatusAPI(params: { ids: string; newStatus: number }) {
  return request<CommonResult<number>>({
    url: '/product/update/newStatus',
    method: 'post',
    params,
  })
}

export function productUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  return request<CommonResult<number>>({
    url: '/product/update/recommendStatus',
    method: 'post',
    params,
  })
}

export function productUpdatePublishStatusAPI(params: { ids: string; publishStatus: number }) {
  return request<CommonResult<number>>({
    url: '/product/update/publishStatus',
    method: 'post',
    params,
  })
}
