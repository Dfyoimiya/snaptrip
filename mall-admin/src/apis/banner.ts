import type { CommonResult, CommonPage } from '@/types/common'
import type { SmsHomeAdvertise } from '@/types/banner'
import request from '@/utils/request'

export function getHomeAdvertiseListAPI(params: { name?: string; type?: number; endTime?: string; pageNum: number; pageSize: number }) {
  return request<CommonResult<CommonPage<SmsHomeAdvertise>>>({
    url: '/home/advertise/list',
    method: 'get',
    params,
  })
}

export function homeAdvertiseCreateAPI(data: SmsHomeAdvertise) {
  return request<CommonResult<number>>({
    url: '/home/advertise/create',
    method: 'post',
    data,
  })
}

export function homeAdvertiseUpdateAPI(id: number, data: SmsHomeAdvertise) {
  return request<CommonResult<number>>({
    url: '/home/advertise/update/' + id,
    method: 'post',
    data,
  })
}

export function getHomeAdvertiseByIdAPI(id: number) {
  return request<CommonResult<SmsHomeAdvertise>>({
    url: '/home/advertise/' + id,
    method: 'get',
  })
}

export function deleteHomeAdvertiseAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/home/advertise/delete',
    method: 'post',
    params,
  })
}

export function homeAdvertiseUpdateStatusAPI(params: { id: number; status: number }) {
  return request<CommonResult<number>>({
    url: '/home/advertise/update/status/' + params.id,
    method: 'post',
    params,
  })
}

// 向后兼容别名
export const fetchBannerList = getHomeAdvertiseListAPI
export const saveBanner = homeAdvertiseCreateAPI
export const deleteBanner = deleteHomeAdvertiseAPI
export const updateBannerStatus = homeAdvertiseUpdateStatusAPI
