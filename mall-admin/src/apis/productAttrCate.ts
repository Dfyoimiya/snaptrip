import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProductAttributeCategory, PmsProductAttributeCategoryExt } from '@/types/productAttr'
import request from '@/utils/request'

/**
 * 获取所有商品属性分类及其下属性
 */
export function productAttributeCategoryListWithAttrAPI() {
  return request<CommonResult<PmsProductAttributeCategoryExt[]>>({
    url: '/productAttribute/category/list/withAttr',
    method: 'get',
  })
}

/**
 * 分页获取所有商品属性分类
 */
export function getProductAttributeCategoryListAPI(params: { pageNum: number; pageSize: number }) {
  return request<CommonResult<CommonPage<PmsProductAttributeCategory>>>({
    url: '/productAttribute/category/list',
    method: 'get',
    params,
  })
}

/**
 * 添加商品属性分类
 */
export function productAttributeCategoryCreateAPI(name: string) {
  return request<CommonResult<number>>({
    url: '/productAttribute/category/create',
    method: 'post',
    params: { name },
  })
}

/**
 * 修改商品属性分类
 */
export function productAttributeCategoryUpdateAPI(id: number, name: string) {
  return request<CommonResult<number>>({
    url: '/productAttribute/category/update/' + id,
    method: 'post',
    params: { name },
  })
}

/**
 * 删除单个商品属性分类
 */
export function productAttributeCategoryDeleteById(id: number) {
  return request<CommonResult<number>>({
    url: '/productAttribute/category/delete/' + id,
    method: 'get',
  })
}
