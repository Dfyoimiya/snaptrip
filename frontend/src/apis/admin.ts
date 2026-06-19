import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'
import type { UmsAdmin } from '@/types/admin'
import type { PageParam } from '@/types/common'

export function getAdminListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<UmsAdmin>>>({ url: '/admin/list', method: 'get', params })
}

export function adminRegisterAPI(data: UmsAdmin) {
  return request<CommonResult<UmsAdmin>>({
    url: '/admin/register',
    method: 'post',
    data: {
      email: data.email || '',
      password: data.password,
      role_ids: data.roleIds || [],
    },
  })
}

export function adminUpdateByIdAPI(id: string, data: UmsAdmin) {
  return request<CommonResult<number>>({
    url: '/admin/update/' + id,
    method: 'post',
    data: {
      email: data.email || undefined,
      password: data.password || undefined,
      is_active: data.isActive,
      role_ids: data.roleIds,
    },
  })
}

export function adminUpdateStatusByIdAPI(id: string, params: { status: number }) {
  return request<CommonResult<number>>({ url: '/admin/updateStatus/' + id, method: 'post', params })
}

export function adminDeleteByIdAPI(id: string) {
  return request<CommonResult<number>>({ url: '/admin/delete/' + id, method: 'post' })
}

export function getRoleByAdminIdAPI(adminId: string) {
  return request<CommonResult<Array<{ id: string; name: string }>>>({
    url: '/admin/role/' + adminId,
    method: 'get',
  })
}

export function adminRoleUpdateAPI(data: { adminId: string; roleIds: string[] }) {
  return request<CommonResult<number>>({
    url: '/admin/role/update',
    method: 'post',
    data: {
      admin_id: data.adminId,
      role_ids: data.roleIds,
    },
  })
}
