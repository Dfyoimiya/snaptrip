import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProductAttribute, ProductAttrInfo } from '@/types/productAttr'
import request from '@/utils/request'

/**
 * 根据商品分类ID获取商品属性及属性分类ID
 */
export function getProductAttrInfoByCateIdAPI(cateId: number) {
  return request<CommonResult<ProductAttrInfo[]>>({
    url: '/productAttribute/attrInfo/' + cateId,
    method: 'get',
  })
}

/**
 * 根据分类ID查询属性列表或参数列表
 */
export function getProductAttributeListAPI(
  productAttributeCategoryId: number,
  params: { pageNum: number; pageSize: number; type: number }
) {
  return request<CommonResult<CommonPage<PmsProductAttribute>>>({
    url: '/productAttribute/list/' + productAttributeCategoryId,
    method: 'get',
    params,
  })
}

/**
 * 添加商品属性信息
 */
export function createProductAttributeAPI(data: PmsProductAttribute) {
  return request<CommonResult<number>>({
    url: '/productAttribute/create',
    method: 'post',
    data,
  })
}

/**
 * 修改商品属性信息
 */
export function updateProductAttributeAPI(id: number, data: PmsProductAttribute) {
  return request<CommonResult<number>>({
    url: '/productAttribute/update/' + id,
    method: 'post',
    data,
  })
}

/**
 * 根据ID查询商品属性
 */
export function getProductAttributeAPI(id: number) {
  return request<CommonResult<PmsProductAttribute>>({
    url: '/productAttribute/' + id,
    method: 'get',
  })
}

/**
 * 批量删除商品属性
 */
export function deleteProductAttributeAPI(params: { ids: string }) {
  return request<CommonResult<number>>({
    url: '/productAttribute/delete',
    method: 'post',
    params,
  })
}
