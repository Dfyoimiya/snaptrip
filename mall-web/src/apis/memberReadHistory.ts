/**
 * ============================================
 * 会员浏览记录 API
 * 对应原项目 apis/memberReadHistory.ts
 * ============================================
 */

import request from '@/utils/request'
import type { MemberReadHistory } from '@/types/memberReadHistory'
import type { CommonPage } from '@/types/common'

/** 创建浏览记录 */
export const createReadHistoryAPI = (data: MemberReadHistory) => {
  return request({
    method: 'POST',
    url: '/member/readHistory/create',
    data,
  })
}

/** 删除浏览记录 */
export const deleteReadHistoryAPI = (params: { ids: string[] }) => {
  return request({
    method: 'POST',
    url: '/member/readHistory/delete',
    params,
  })
}

/** 获取浏览记录列表 */
export const fetchReadHistoryListAPI = (params: { pageNum: number; pageSize: number }) => {
  return request<CommonPage<MemberReadHistory>>({
    method: 'GET',
    url: '/member/readHistory/list',
    params,
  })
}

/** 清空浏览记录 */
export const clearReadHistoryAPI = () => {
  return request({
    method: 'POST',
    url: '/member/readHistory/clear',
  })
}
