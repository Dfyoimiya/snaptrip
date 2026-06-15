import request from '@/utils/request'
import type { CommonResult, CommonPage } from '@/types/common'

export interface MemberAdminItem {
  id: string
  email: string
  is_active: boolean
  created_at: string | null
}

export function getMemberListAPI(params: {
  keyword?: string
  is_active?: boolean
  page?: number
  page_size?: number
}) {
  return request<CommonResult<CommonPage<MemberAdminItem>>>({
    url: '/admin/members',
    method: 'get',
    params,
  })
}

export function getMemberDetailAPI(id: string) {
  return request<CommonResult<Record<string, any>>>({
    url: '/admin/members/' + id,
    method: 'get',
  })
}

export function toggleMemberStatusAPI(id: string, is_active: boolean) {
  return request<CommonResult<any>>({
    url: '/admin/members/' + id + '/status',
    method: 'patch',
    params: { is_active },
  })
}
