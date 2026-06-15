import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsBrand } from '@/types/brand'
import request from '@/utils/request'

/** 品牌分页列表 —— GET /admin/brands */
export function getBrandListAPI(params: { keyword?: string; page: number; page_size: number }) {
  return request<CommonResult<CommonPage<PmsBrand>>>({
    url: '/admin/brands',
    method: 'get',
    params,
  })
}

/** 全部启用品牌 —— GET /admin/brands/all */
export function getBrandAllAPI() {
  return request<CommonResult<PmsBrand[]>>({
    url: '/admin/brands/all',
    method: 'get',
  })
}

/** 创建品牌 —— POST /admin/brands */
export function createBrandAPI(data: PmsBrand) {
  return request<CommonResult<number>>({
    url: '/admin/brands',
    method: 'post',
    data,
  })
}

/** 编辑品牌 —— PUT /admin/brands/{id} */
export function updateBrandAPI(id: string, data: PmsBrand) {
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id,
    method: 'put',
    data,
  })
}

/** 品牌详情 —— GET /admin/brands/{id} */
export function getBrandAPI(id: string) {
  return request<CommonResult<PmsBrand>>({
    url: '/admin/brands/' + id,
    method: 'get',
  })
}

/** 删除品牌 —— DELETE /admin/brands/{id} */
export function brandDeleteByIdAPI(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id,
    method: 'delete',
  })
}

/** 切换品牌显示状态 —— PATCH /admin/brands/{id}/status?field=show_status&status=0|1 */
export function brandUpdateShowStatusAPI(id: string, showStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id + '/status',
    method: 'patch',
    params: { field: 'show_status', status: showStatus },
  })
}

/** 切换品牌制造商状态 —— PATCH /admin/brands/{id}/status?field=factory_status&status=0|1 */
export function brandUpdateFactoryStatusAPI(id: string, factoryStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/brands/' + id + '/status',
    method: 'patch',
    params: { field: 'factory_status', status: factoryStatus },
  })
}
