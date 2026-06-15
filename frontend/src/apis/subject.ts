import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import type { CmsSubject, CmsSubjectCategory } from '@/types/subject'
import request from '@/utils/request'

// ── 分类名 ↔ ID 映射（运行时缓存） ──

let _categoryNameToId: Record<string, string> | null = null

async function _loadCategoryMap(): Promise<Record<string, string>> {
  if (_categoryNameToId) return _categoryNameToId
  const res = await request<CommonResult<CmsSubjectCategory[]>>({
    url: '/admin/cms/subjects/categories',
    method: 'get',
  })
  const map: Record<string, string> = {}
  for (const c of res.data) {
    if (c.name && c.id) map[c.name] = c.id
  }
  _categoryNameToId = map
  return map
}

function _resolveCategoryId(name: string | undefined, map: Record<string, string>): string | undefined {
  if (!name) return undefined
  return map[name]
}

function _resolveCategoryName(id: string | undefined, map: Record<string, string>): string | undefined {
  if (id === undefined) return undefined
  for (const [name, cid] of Object.entries(map)) {
    if (cid === id) return name
  }
  return undefined
}

// ── 导出 API ──

/** 全量专题列表（用于下拉等） —— GET /admin/cms/subjects */
export function getSubjectListAllAPI() {
  return request<CommonResult<CmsSubject[]>>({
    url: '/admin/cms/subjects',
    method: 'get',
    params: { page_size: 100 },
  }).then(res => ({ ...res, data: res.data.map((i: any) => ({ ...i, showStatus: i.status })) }))
}

/** 分页专题列表 —— GET /admin/cms/subjects */
export async function getSubjectListAPI(params: PageParam) {
  const catMap = await _loadCategoryMap()
  const res = await request<CommonResult<CommonPage<CmsSubject>>>({
    url: '/admin/cms/subjects',
    method: 'get',
    params,
  })
  // 映射后端字段 → 前端类型期望
  if (res.data?.items) {
    res.data.items = res.data.items.map((item: any) => ({
      ...item,
      showStatus: item.status,           // status → showStatus
      categoryId: _resolveCategoryId(item.categoryName, catMap),
      description: item.summary,          // summary → description
    }))
  }
  return res
}

/** 专题分类列表 —— GET /admin/cms/subjects/categories */
export async function fetchSubjectCategoryList() {
  _categoryNameToId = null  // 刷新缓存
  const catMap = await _loadCategoryMap()
  const items: CmsSubjectCategory[] = Object.entries(catMap).map(
    ([name, id]) => ({ id, name })
  )
  return { code: 200, data: items, message: 'success' }
}

/** 保存专题（创建或编辑） —— POST/PUT /admin/cms/subjects */
export async function saveSubject(data: CmsSubject) {
  const catMap = await _loadCategoryMap()
  const payload: Record<string, any> = {
    title: data.title,
    pic: data.pic,
    status: data.showStatus,               // showStatus → status
    recommend_status: data.recommendStatus,
    summary: data.description,              // description → summary
    content: (data as any).content,
    category_name: _resolveCategoryName(data.categoryId, catMap),
  }
  if ((data as any).id) {
    return request<CommonResult<number>>({
      url: '/admin/cms/subjects/' + (data as any).id,
      method: 'put',
      data: payload,
    })
  }
  return request<CommonResult<number>>({
    url: '/admin/cms/subjects',
    method: 'post',
    data: payload,
  })
}

/** 删除专题 —— DELETE /admin/cms/subjects/{id} */
export function deleteSubject(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/cms/subjects/' + id,
    method: 'delete',
  })
}

/** 更新推荐状态 —— PUT /admin/cms/subjects/{id} */
export function updateSubjectRecommendStatus(id: string, status: number) {
  return request<CommonResult<number>>({
    url: '/admin/cms/subjects/' + id,
    method: 'put',
    data: { recommend_status: status },
  })
}

/** 更新展示状态 —— PUT /admin/cms/subjects/{id} */
export function updateSubjectShowStatus(id: string, status: number) {
  return request<CommonResult<number>>({
    url: '/admin/cms/subjects/' + id,
    method: 'put',
    data: { status },
  })
}

// 向后兼容别名（视图层使用）
export const fetchSubjectList = getSubjectListAPI
