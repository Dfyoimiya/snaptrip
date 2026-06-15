import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import request from '@/utils/request'

export interface CmsHelp {
  id?: number
  title?: string
  content?: string
  categoryName?: string
  status?: number
  sort?: number
  createdAt?: string
}

/** 帮助分页列表 —— GET /admin/cms/helps */
export function getHelpListAPI(params: PageParam & { category_name?: string; status?: number }) {
  return request<CommonResult<CommonPage<CmsHelp>>>({
    url: '/admin/cms/helps',
    method: 'get',
    params: {
      category_name: params.category_name,
      status: params.status,
      page: params.page,
      page_size: params.page_size,
    },
  })
}

/** 创建帮助 —— POST /admin/cms/helps */
export function helpCreateAPI(data: CmsHelp) {
  return request<CommonResult<number>>({
    url: '/admin/cms/helps',
    method: 'post',
    data: {
      title: data.title,
      content: data.content,
      category_name: data.categoryName,
      status: data.status ?? 1,
      sort: data.sort ?? 0,
    },
  })
}

/** 编辑帮助 —— PUT /admin/cms/helps/{id} */
export function helpUpdateByIdAPI(id: number, data: CmsHelp) {
  return request<CommonResult<number>>({
    url: '/admin/cms/helps/' + String(id),
    method: 'put',
    data: {
      title: data.title,
      content: data.content,
      category_name: data.categoryName,
      status: data.status,
      sort: data.sort,
    },
  })
}

/** 删除帮助 —— DELETE /admin/cms/helps/{id} */
export function helpDeleteByIdAPI(id: number) {
  return request<CommonResult<number>>({
    url: '/admin/cms/helps/' + String(id),
    method: 'delete',
  })
}
