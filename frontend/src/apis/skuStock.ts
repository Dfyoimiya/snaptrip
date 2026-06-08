import type { CommonResult } from '@/types/common'
import type { SkuStock } from '@/types/product'
import request from '@/utils/request'

/**
 * 根据商品ID及sku编码模糊搜索sku库存
 */
export function getSkuListByPidAPI(pid: number, params?: { keyword?: string }) {
  return request<CommonResult<SkuStock[]>>({
    url: '/sku/' + pid,
    method: 'get',
    params,
  })
}

/**
 * 根据商品ID批量更新sku库存信息
 */
export function skuUpdateByPidAPI(pid: number, data: SkuStock[]) {
  return request<CommonResult<number>>({
    url: '/sku/update/' + pid,
    method: 'post',
    data,
  })
}
