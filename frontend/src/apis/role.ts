import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { UmsRole } from '@/types/role'
import type { PageParam } from '@/types/common'

export function getRoleListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<UmsRole>>>({ url: '/role/list', method: 'get', params })
}

export function getRoleListAllAPI() {
  return request<CommonResult<UmsRole[]>>({ url: '/role/listAll', method: 'get' })
}

export function roleCreateAPI(data: UmsRole) {
  return request<CommonResult<number>>({ url: '/role/create', method: 'post', data })
}

export function roleUpdateByIdAPI(id: number, data: UmsRole) {
  return request<CommonResult<number>>({ url: '/role/update/' + id, method: 'post', data })
}

export function roleUpdateStatusAPI(id: number, params: { status: number }) {
  return request<CommonResult<number>>({ url: '/role/updateStatus/' + id, method: 'post', params })
}

export function roleDeleteByIdsAPI(params: { ids: string }) {
  return request<CommonResult<number>>({ url: '/role/delete', method: 'post', params })
}

export function getMenuByRoleIdAPI(roleId: number) {
  return request<CommonResult<UmsMenu[]>>({ url: '/role/listMenu/' + roleId, method: 'get' })
}

export function getResourceByRoleIdAPI(roleId: number) {
  return request<CommonResult<UmsResource[]>>({ url: '/role/listResource/' + roleId, method: 'get' })
}

export function roleAllocMenuAPI(data: { roleId: number; menuIds: string }) {
  return request<CommonResult<number>>({ url: '/role/allocMenu', method: 'post', data })
}

export function roleAllocResourceAPI(data: { roleId: number; resourceIds: string }) {
  return request<CommonResult<number>>({ url: '/role/allocResource', method: 'post', data })
}

import type { UmsMenu } from '@/types/menu'
import type { UmsResource } from '@/types/resource'
