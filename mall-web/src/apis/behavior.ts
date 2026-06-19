/**
 * ============================================
 * 用户行为 API
 * 浏览历史、搜索历史查询
 * ============================================
 */

import { get, del } from '@/utils/request'
import type { CommonPage } from '@/types/common'

export interface BehaviorItem {
  id: string
  behaviorType: string
  itemId: string | null
  itemType: string | null
  createdAt: string | null
  productName: string | null
  productPic: string | null
  productPrice: number | null
}

/**
 * 查询用户行为历史
 * @param behaviorType 行为类型: view/search/add_cart/purchase/favorite
 * @param page 页码
 * @param pageSize 每页数量
 */
export const getBehaviorsAPI = (
  behaviorType?: string,
  page = 1,
  pageSize = 20,
) => {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (behaviorType) params.behavior_type = behaviorType
  return get<CommonPage<BehaviorItem>>('/api/v1/portal/behaviors', params)
}

/** 清空/批量删除行为历史 */
export const deleteBehaviorsAPI = (behaviorType?: string, ids?: string) => {
  const params: Record<string, unknown> = {}
  if (behaviorType) params.behavior_type = behaviorType
  if (ids) params.ids = ids
  return del<{ deleted: number; message: string }>('/api/v1/portal/behaviors', params)
}
