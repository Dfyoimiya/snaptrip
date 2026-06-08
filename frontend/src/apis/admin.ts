import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { UmsAdmin } from '@/types/admin'
import type { PageParam } from '@/types/common'

export function getAdminListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<UmsAdmin>>>({ url: '/admin/list', method: 'get', params })
}

export function adminRegisterAPI(data: UmsAdmin) {
  return request<CommonResult<UmsAdmin>>({ url: '/admin/register', method: 'post', data })
}

export function adminUpdateByIdAPI(id: number, data: UmsAdmin) {
  return request<CommonResult<number>>({ url: '/admin/update/' + id, method: 'post', data })
}

export function adminUpdateStatusByIdAPI(id: number, params: { status: number }) {
  return request<CommonResult<number>>({ url: '/admin/updateStatus/' + id, method: 'post', params })
}

export function adminDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({ url: '/admin/delete/' + id, method: 'post' })
}

export function getRoleByAdminIdAPI(adminId: number) {
  return request<CommonResult<any[]>>({ url: '/admin/role/' + adminId, method: 'get' })
}

export function adminRoleUpdateAPI(params: { adminId: number; roleIds: string }) {
  return request<CommonResult<number>>({ url: '/admin/role/update', method: 'post', params })
}
