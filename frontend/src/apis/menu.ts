import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import type { UmsMenu, UmsMenuNode } from '@/types/menu'

export function getMenuTreeListAPI() {
  return request<CommonResult<UmsMenuNode[]>>({ url: '/menu/treeList', method: 'get' })
}

export function getMenuListByParentIdAPI(parentId: number, params: PageParam) {
  return request<CommonResult<CommonPage<UmsMenu>>>({
    url: '/menu/list/' + parentId,
    method: 'get',
    params,
  })
}

export function menuCreateAPI(data: UmsMenu) {
  return request<CommonResult<number>>({ url: '/menu/create', method: 'post', data })
}

export function menuUpdateByIdAPI(id: number, data: UmsMenu) {
  return request<CommonResult<number>>({ url: '/menu/update/' + id, method: 'post', data })
}

export function menuDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({ url: '/menu/delete/' + id, method: 'post' })
}

export function getMenuByIdAPI(id: number) {
  return request<CommonResult<UmsMenu>>({
    url: '/menu/' + id,
    method: 'get',
  })
}

export function menuUpdateHiddenByIdAPI(id: number, params: { hidden: number }) {
  return request<CommonResult<number>>({ url: '/menu/updateHidden/' + id, method: 'post', params })
}
