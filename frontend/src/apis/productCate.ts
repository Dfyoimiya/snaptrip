import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProductCategory } from '@/types/productCate'
import request from '@/utils/request'

export function getProductCategoryListAPI(parentId: number, params: { pageNum: number; pageSize: number }) {
  return request<CommonResult<CommonPage<PmsProductCategory>>>({
    url: '/productCategory/list/' + parentId,
    method: 'get',
    params,
  })
}

export function getProductCategoryListWithChildrenAPI() {
  return request<CommonResult<PmsProductCategory[]>>({
    url: '/productCategory/list/withChildren',
    method: 'get',
  })
}

export function createProductCategoryAPI(data: PmsProductCategory) {
  return request<CommonResult<number>>({
    url: '/productCategory/create',
    method: 'post',
    data,
  })
}

export function updateProductCategoryAPI(id: number, data: PmsProductCategory) {
  return request<CommonResult<number>>({
    url: '/productCategory/update/' + id,
    method: 'post',
    data,
  })
}

export function getProductCategoryAPI(id: number) {
  return request<CommonResult<PmsProductCategory>>({
    url: '/productCategory/' + id,
    method: 'get',
  })
}

export function productCategoryDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/productCategory/delete/' + id,
    method: 'post',
  })
}

export function productCategoryUpdateNavStatusAPI(params: { ids: string; navStatus: number }) {
  return request<CommonResult<number>>({
    url: '/productCategory/update/navStatus',
    method: 'post',
    params,
  })
}

export function productCategoryUpdateShowStatusAPI(params: { ids: string; showStatus: number }) {
  return request<CommonResult<number>>({
    url: '/productCategory/update/showStatus',
    method: 'post',
    params,
  })
}
