import type { CommonResult, CommonPage } from '@/types/common'
import type { UmsMemberLevel } from '@/types/memberLevel'
import request from '@/utils/request'

/** 会员等级列表 —— 后端暂无独立 memberLevel 端点，使用 /admin/members 或保留占位 */
export function getMemberLevelListAPI(params: { defaultStatus: number }) {
  return request<CommonResult<UmsMemberLevel[]>>({
    url: '/admin/member-levels',
    method: 'get',
    params,
  })
}

/** 会员分页列表 —— GET /admin/members（后台管理） */
export function getMemberListAPI(params: { keyword?: string; page: number; page_size: number }) {
  return request<CommonResult<CommonPage<any>>>({
    url: '/admin/members',
    method: 'get',
    params,
  })
}

/** 会员详情 —— GET /admin/members/{id} */
export function getMemberDetailAPI(id: number) {
  return request<CommonResult<any>>({
    url: '/admin/members/' + id,
    method: 'get',
  })
}

/** 启用/封禁会员 —— PATCH /admin/members/{id}/status */
export function toggleMemberStatusAPI(id: number, isActive: boolean) {
  return request<CommonResult<any>>({
    url: '/admin/members/' + id + '/status',
    method: 'patch',
    params: { is_active: isActive },
  })
}
