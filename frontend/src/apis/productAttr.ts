import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProductAttribute, ProductAttrInfo } from '@/types/productAttr'
import request from '@/utils/request'

/**
 * 根据商品分类ID获取商品属性及属性分类ID
 * —— GET /admin/product-attributes?category_id=...
 */
export function getProductAttrInfoByCateIdAPI(cateId: string) {
  return request<CommonResult<ProductAttrInfo[]>>({
    url: '/admin/product-attributes',
    method: 'get',
    params: { category_id: cateId, page_size: 100 },
  })
}

/**
 * 根据分类ID查询属性列表或参数列表
 * —— GET /admin/product-attributes?category_id=...
 */
export function getProductAttributeListAPI(
  productAttributeCategoryId: string,
  params: { pageNum: number; pageSize: number; type: number }
) {
  return request<CommonResult<CommonPage<PmsProductAttribute>>>({
    url: '/admin/product-attributes',
    method: 'get',
    params: { category_id: productAttributeCategoryId || undefined, page: params.pageNum, page_size: params.pageSize },
  })
}

/**
 * 添加商品属性信息 —— POST /admin/product-attributes
 */
export function createProductAttributeAPI(data: PmsProductAttribute) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes',
    method: 'post',
    data,
  })
}

/**
 * 修改商品属性信息 —— PUT /admin/product-attributes/{id}
 */
export function updateProductAttributeAPI(id: string, data: PmsProductAttribute) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes/' + id,
    method: 'put',
    data,
  })
}

/**
 * 根据ID查询商品属性 —— GET /admin/product-attributes/{id}
 */
export function getProductAttributeAPI(id: string) {
  return request<CommonResult<PmsProductAttribute>>({
    url: '/admin/product-attributes/' + id,
    method: 'get',
  })
}

/**
 * 删除商品属性 —— DELETE /admin/product-attributes/{id}
 */
export function deleteProductAttributeAPI(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/product-attributes/' + id,
    method: 'delete',
  })
}
