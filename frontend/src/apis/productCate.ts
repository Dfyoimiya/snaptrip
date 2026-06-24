import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProductCategory } from '@/types/productCate'
import request from '@/utils/request'

function normalizeParentId(parentId: string | number | null | undefined) {
  if (parentId === 0 || parentId === '0' || parentId === '') return null
  return parentId ?? null
}

function toCategoryPayload(data: PmsProductCategory) {
  return {
    name: data.name,
    type: data.type || 'PRODUCT',
    parent_id: normalizeParentId(data.parentId),
    sort: data.sort,
    nav_status: data.navStatus,
    show_status: data.showStatus,
    icon: data.icon || null,
    keywords: data.keywords || null,
    description: data.description || null,
  }
}

/** 分页子分类 —— GET /admin/categories?parent_id=... */
export function getProductCategoryListAPI(parentId: string, params: { pageNum: number; pageSize: number }) {
  return request<CommonResult<CommonPage<PmsProductCategory>>>({
    url: '/admin/categories',
    method: 'get',
    params: { parent_id: parentId || undefined, page: params.pageNum, page_size: params.pageSize },
  })
}

/** 分类树形结构 —— GET /admin/categories/tree */
export function getProductCategoryListWithChildrenAPI() {
  return request<CommonResult<PmsProductCategory[]>>({
    url: '/admin/categories/tree',
    method: 'get',
  })
}

/** 创建分类 —— POST /admin/categories */
export function createProductCategoryAPI(data: PmsProductCategory) {
  return request<CommonResult<number>>({
    url: '/admin/categories',
    method: 'post',
    data: toCategoryPayload(data),
  })
}

/** 编辑分类 —— PUT /admin/categories/{id} */
export function updateProductCategoryAPI(id: string, data: PmsProductCategory) {
  return request<CommonResult<number>>({
    url: '/admin/categories/' + id,
    method: 'put',
    data: toCategoryPayload(data),
  })
}

/** 分类详情 —— GET /admin/categories/{id} */
export function getProductCategoryAPI(id: string) {
  return request<CommonResult<PmsProductCategory>>({
    url: '/admin/categories/' + id,
    method: 'get',
  })
}

/** 删除分类 —— DELETE /admin/categories/{id} */
export function productCategoryDeleteByIdAPI(id: string, force = false) {
  return request<CommonResult<number>>({
    url: '/admin/categories/' + id,
    method: 'delete',
    params: { force },
  })
}

/** 切换导航显示状态 —— PATCH /admin/categories/{id}/status?field=nav_status&status=0|1 */
export function productCategoryUpdateNavStatusAPI(id: string, navStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/categories/' + id + '/status',
    method: 'patch',
    params: { field: 'nav_status', status: navStatus },
  })
}

/** 切换显示状态 —— PATCH /admin/categories/{id}/status?field=show_status&status=0|1 */
export function productCategoryUpdateShowStatusAPI(id: string, showStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/categories/' + id + '/status',
    method: 'patch',
    params: { field: 'show_status', status: showStatus },
  })
}

/** 批量更新排序（拖拽后调用） —— PATCH /admin/categories/batch-sort */
export function productCategoryBatchSortAPI(data: { items: { id: string; sort: number }[] }) {
  return request<CommonResult<{ id: string; sort: number }[]>>({
    url: '/admin/categories/batch-sort',
    method: 'patch',
    data,
  })
}

/** 移动分类到新的父分类下 —— PATCH /admin/categories/{id}/move */
export function productCategoryMoveAPI(id: string, parentId: string | number | null) {
  return request<CommonResult<PmsProductCategory>>({
    url: '/admin/categories/' + id + '/move',
    method: 'patch',
    data: { parent_id: normalizeParentId(parentId) },
  })
}
