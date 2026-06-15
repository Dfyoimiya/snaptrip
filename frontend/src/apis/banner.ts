import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeAdvertise } from '@/types/banner'
import request from '@/utils/request'

/** 轮播图分页列表 —— GET /admin/cms/banners */
export function getBannerListAPI(params?: { status?: number }) {
  return request<CommonResult<CommonPage<SmsHomeAdvertise>>>({
    url: '/admin/cms/banners',
    method: 'get',
    params,
  }).then(res => {
    // Backend returns flat list; wrap in CommonPage shape for view compatibility
    const items = Array.isArray(res.data) ? res.data : (res.data as any)?.items ?? []
    return { ...res, data: { items, total: items.length } } as typeof res
  })
}

/** 创建轮播图 —— POST /admin/cms/banners */
export function bannerCreateAPI(data: SmsHomeAdvertise) {
  return request<CommonResult<string>>({
    url: '/admin/cms/banners',
    method: 'post',
    data: {
      name: data.name,
      pic: data.pic,
      url: data.url,
      type: data.type,
      status: data.status,
      sort: data.sort,
      note: data.note,
      start_time: data.startTime,
      end_time: data.endTime,
    },
  })
}

/** 编辑轮播图 —— PUT /admin/cms/banners/{id} */
export function bannerUpdateAPI(id: string, data: SmsHomeAdvertise) {
  return request<CommonResult<string>>({
    url: '/admin/cms/banners/' + id,
    method: 'put',
    data: {
      name: data.name,
      pic: data.pic,
      url: data.url,
      type: data.type,
      status: data.status,
      sort: data.sort,
      note: data.note,
      start_time: data.startTime,
      end_time: data.endTime,
    },
  })
}

/** 删除轮播图 —— DELETE /admin/cms/banners/{id} */
export function bannerDeleteAPI(id: string) {
  return request<CommonResult<string>>({
    url: '/admin/cms/banners/' + id,
    method: 'delete',
  })
}

/** 切换轮播图状态 —— PATCH /admin/cms/banners/{id}/status */
export function bannerUpdateStatusAPI(id: string, status: number) {
  return request<CommonResult<string>>({
    url: '/admin/cms/banners/' + id + '/status',
    method: 'patch',
    params: { status },
  })
}

/** 修改排序 —— PATCH /admin/cms/banners/{id}/sort */
export function bannerUpdateSortAPI(id: string, sort: number) {
  return request<CommonResult<string>>({
    url: '/admin/cms/banners/' + id + '/sort',
    method: 'patch',
    params: { sort },
  })
}

// ── 向后兼容别名（视图层使用） ──

/** @deprecated 使用 getBannerListAPI */
export const fetchBannerList = getBannerListAPI

/** 保存（自动判断创建/编辑） */
export async function saveBanner(data: SmsHomeAdvertise) {
  if (data.id) {
    return bannerUpdateAPI(data.id, data)
  }
  return bannerCreateAPI(data)
}

/** @deprecated 使用 bannerDeleteAPI */
export async function deleteBanner(id: string) {
  return bannerDeleteAPI(id)
}

/** @deprecated 使用 bannerUpdateStatusAPI */
export const updateBannerStatus = bannerUpdateStatusAPI
