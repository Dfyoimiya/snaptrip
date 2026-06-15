import type { CommonResult } from '@/types/common'
import type { PmsProductAttributeCategoryExt } from '@/types/productAttr'
import request from '@/utils/request'

/**
 * 获取所有商品属性分类及其下属性
 * GET /admin/product-attributes/categories
 */
export function productAttributeCategoryListWithAttrAPI() {
  return request<CommonResult<PmsProductAttributeCategoryExt[]>>({
    url: '/admin/product-attributes/categories',
    method: 'get',
  })
}

/**
 * 添加商品属性分类
 * POST /admin/product-attributes/categories?name=...
 */
export function productAttributeCategoryCreateAPI(name: string) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes/categories',
    method: 'post',
    params: { name },
  })
}

/**
 * 修改商品属性分类
 * PUT /admin/product-attributes/categories/{id}?name=...
 */
export function productAttributeCategoryUpdateAPI(id: string, name: string) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes/categories/' + id,
    method: 'put',
    params: { name },
  })
}

/**
 * 删除单个商品属性分类
 * DELETE /admin/product-attributes/categories/{id}
 */
export function productAttributeCategoryDeleteById(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes/categories/' + id,
    method: 'delete',
  })
}
