import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { UmsResource, UmsResourceCategory } from '@/types/resource'
import type { PageParam } from '@/types/common'

export function getResourceCategoryListAllAPI() {
  return request<CommonResult<UmsResourceCategory[]>>({ url: '/resourceCategory/listAll', method: 'get' })
}

export function fetchAllResourceList() {
  return request<CommonResult<UmsResource[]>>({ url: '/resource/listAll', method: 'get' })
}

export function getResourceListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<UmsResource>>>({ url: '/resource/list', method: 'get', params })
}

export function resourceCreateAPI(data: UmsResource) {
  return request<CommonResult<number>>({ url: '/resource/create', method: 'post', data })
}

export function resourceUpdateByIdAPI(id: number, data: UmsResource) {
  return request<CommonResult<number>>({ url: '/resource/update/' + id, method: 'post', data })
}

export function resourceDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({ url: '/resource/delete/' + id, method: 'post' })
}

export function resourceCategoryCreateAPI(data: UmsResourceCategory) {
  return request<CommonResult<number>>({ url: '/resourceCategory/create', method: 'post', data })
}

export function resourceCategoryUpdateByIdAPI(id: number, data: UmsResourceCategory) {
  return request<CommonResult<number>>({ url: '/resourceCategory/update/' + id, method: 'post', data })
}

export function resourceCategoryDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({ url: '/resourceCategory/delete/' + id, method: 'post' })
}
