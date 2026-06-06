import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsBrand } from '@/types/brand'
import request from '@/utils/request'

export function getBrandListAPI(params: { keyword?: string; pageNum: number; pageSize: number }) {
  return request<CommonResult<CommonPage<PmsBrand>>>({
    url: '/brand/list',
    method: 'get',
    params,
  })
}

export function createBrandAPI(data: PmsBrand) {
  return request<CommonResult<number>>({
    url: '/brand/create',
    method: 'post',
    data,
  })
}

export function updateBrandAPI(id: number, data: PmsBrand) {
  return request<CommonResult<number>>({
    url: '/brand/update/' + id,
    method: 'post',
    data,
  })
}

export function getBrandAPI(id: number) {
  return request<CommonResult<PmsBrand>>({
    url: '/brand/' + id,
    method: 'get',
  })
}

export function brandDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/brand/delete/' + id,
    method: 'get',
  })
}

export function brandUpdateShowStatusAPI(params: { ids: string; showStatus: number }) {
  return request<CommonResult<number>>({
    url: '/brand/update/showStatus',
    method: 'post',
    params,
  })
}

export function brandUpdateFactoryStatusAPI(params: { ids: string; factoryStatus: number }) {
  return request<CommonResult<number>>({
    url: '/brand/update/factoryStatus',
    method: 'post',
    params,
  })
}
