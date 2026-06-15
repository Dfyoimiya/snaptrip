import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeBrand } from '@/types/homeBrand'
import request from '@/utils/request'

/** 品牌推荐分页列表 —— GET /admin/brands（后端BrandResponse含sort字段即视作推荐序） */
export function getHomeBrandListAPI(params: { pageNum: number; pageSize: number; brandName?: string; recommendStatus?: number }) {
  return request<CommonResult<CommonPage<SmsHomeBrand>>>({
    url: '/admin/brands',
    method: 'get',
    params: {
      keyword: params.brandName,
      show_status: params.recommendStatus,
      page: params.pageNum,
      page_size: params.pageSize,
    },
  })
}

/** 添加品牌推荐 —— POST /admin/brands（创建品牌并标记show_status） */
export function homeBrandCreateAPI(data: SmsHomeBrand[]) {
  const item = data[0] || (data as any)
  return request<CommonResult<number>>({
    url: '/admin/brands',
    method: 'post',
    data: {
      name: item.brandName,
      show_status: item.recommendStatus ?? 1,
      sort: item.sort ?? 0,
    },
  })
}

/** 更新推荐状态 —— PUT /admin/brands/{id} */
export function homeBrandUpdateRecommendStatusAPI(params: { ids: string; recommendStatus: number }) {
  const id = params.ids.split(',')[0]
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id,
    method: 'put',
    data: { show_status: params.recommendStatus },
  })
}

/** 删除品牌推荐（按ID） —— DELETE /admin/brands/{id} */
export function homeBrandDeleteByIdsAPI(params: { ids: string }) {
  const id = params.ids.split(',')[0]
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id,
    method: 'delete',
  })
}

/** 更新品牌排序 —— PUT /admin/brands/{id} */
export function homeBrandUpdateSortAPI(params: { id: string; sort: number }) {
  return request<CommonResult<number>>({
    url: '/admin/brands/' + params.id,
    method: 'put',
    data: { sort: params.sort },
  })
}

// 向后兼容别名（视图层使用）
export const fetchHomeBrandList = getHomeBrandListAPI
export const addHomeBrand = homeBrandCreateAPI
export const deleteHomeBrand = homeBrandDeleteByIdsAPI
export const updateHomeBrandSort = homeBrandUpdateSortAPI
export const updateHomeBrandStatus = homeBrandUpdateRecommendStatusAPI
export const batchDeleteHomeBrand = homeBrandDeleteByIdsAPI
