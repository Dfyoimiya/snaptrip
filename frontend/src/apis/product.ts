import type { CommonResult, CommonPage } from '@/types/common'
import type { PmsProduct, ProductQueryParam, PmsProductParam } from '@/types/product'
import request from '@/utils/request'

/** 映射前端查询参数 → 后端 snake_case 查询参数 */
function mapProductParams(params: ProductQueryParam) {
  return {
    keyword: params.keyword,
    product_sn: params.productSn,
    category_id: params.categoryId,
    brand_id: params.brandId,
    publish_status: params.publishStatus,
    verify_status: params.verifyStatus,
    page: params.page,
    page_size: params.page_size,
  }
}

/** 商品分页列表 —— GET /admin/products */
export function getProductListAPI(params: ProductQueryParam) {
  return request<CommonResult<CommonPage<PmsProduct>>>({
    url: '/admin/products',
    method: 'get',
    params: mapProductParams(params),
  })
}

/** 创建商品 —— POST /admin/products */
export function createProductAPI(data: PmsProductParam) {
  return request<CommonResult<number>>({
    url: '/admin/products',
    method: 'post',
    data,
  })
}

/** 编辑商品 —— PUT /admin/products/{id} */
export function updateProductAPI(id: string, data: PmsProductParam) {
  return request<CommonResult<number>>({
    url: '/admin/products/' + id,
    method: 'put',
    data,
  })
}

/** 商品详情 —— GET /admin/products/{id} */
export function getProductAPI(id: string) {
  return request<CommonResult<PmsProductParam>>({
    url: '/admin/products/' + id,
    method: 'get',
  })
}

/** 删除商品 —— DELETE /admin/products/{id} */
export function productUpdateDeleteStatusAPI(id: string) {
  return request<CommonResult<number>>({
    url: '/admin/products/' + id,
    method: 'delete',
  })
}

/** 设为新品 —— PATCH /admin/products/{id}/new */
export function productUpdateNewStatusAPI(id: string, newStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/products/' + id + '/new',
    method: 'patch',
    params: { status: newStatus },
  })
}

/** 设为推荐 —— PATCH /admin/products/{id}/recommend */
export function productUpdateRecommendStatusAPI(id: string, recommendStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/products/' + id + '/recommend',
    method: 'patch',
    params: { status: recommendStatus },
  })
}

/** 上架/下架 —— PATCH /admin/products/{id}/status */
export function productUpdatePublishStatusAPI(id: string, publishStatus: number) {
  return request<CommonResult<number>>({
    url: '/admin/products/' + id + '/status',
    method: 'patch',
    params: { status: publishStatus },
  })
}
