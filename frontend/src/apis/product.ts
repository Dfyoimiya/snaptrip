import type { CommonResult, CommonPage } from '@/types/common'
import type {
  PmsProduct,
  ProductDetailResponse,
  ProductCreatePayload,
  ProductQueryParam,
  PmsProductParam,
  ProductSkuPayload,
  ProductUpdatePayload,
  SkuStock,
} from '@/types/product'
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

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function toNullableNumber(value: unknown): number | null {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function toIsoDate(value: unknown): string | null {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(String(value))
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}

function mapSkuPayload(sku: SkuStock): ProductSkuPayload {
  return {
    sku_code: sku.skuCode?.trim() || `SKU-${Date.now()}`,
    spec: sku.spec || sku.spData || '{}',
    price: Math.max(toNumber(sku.price), 0.01),
    promotion_price: toNullableNumber(sku.promotionPrice),
    stock: Math.max(toNumber(sku.stock), 0),
    low_stock: Math.max(toNumber(sku.lowStock), 0),
    pic: sku.defaultPic || null,
  }
}

/** 将商品表单字段映射为 FastAPI snake_case Schema */
export function mapProductPayload(data: PmsProductParam): ProductCreatePayload {
  const promotionEnabled = data.promotionType === 1
  const attributeValues = Object.fromEntries(
    (data.productAttributeValueList || [])
      .filter((item) => item.productAttributeId && item.value !== undefined)
      .map((item) => [item.productAttributeId, item.value]),
  )

  return {
    name: data.name.trim(),
    sub_title: data.subTitle || null,
    brand_id: data.brandId || null,
    category_id: data.categoryId || null,
    product_sn: data.productSn || null,
    price: toNumber(data.price),
    original_price: toNullableNumber(data.originalPrice),
    promotion_price: promotionEnabled ? toNullableNumber(data.promotionPrice) : null,
    promotion_start_time: promotionEnabled ? toIsoDate(data.promotionStartTime) : null,
    promotion_end_time: promotionEnabled ? toIsoDate(data.promotionEndTime) : null,
    promotion_per_limit: Math.max(toNumber(data.promotionPerLimit), 0),
    promotion_type: toNumber(data.promotionType),
    publish_status: toNumber(data.publishStatus),
    new_status: toNumber(data.newStatus),
    recommend_status: toNumber(data.recommendStatus),
    description: data.description || null,
    keywords: data.keywords || null,
    unit: data.unit || null,
    weight: toNullableNumber(data.weight),
    service_ids: data.serviceIds || null,
    freight_template_id: data.freightTemplateId ? String(data.freightTemplateId) : null,
    pics: data.defaultPic || null,
    album_pics: data.albumPics || null,
    default_pic: data.defaultPic || null,
    skus: (data.skuStockList || []).map(mapSkuPayload),
    attribute_values: attributeValues,
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
  return request<CommonResult<PmsProduct>>({
    url: '/admin/products',
    method: 'post',
    data: mapProductPayload(data),
  })
}

/** 编辑商品 —— PUT /admin/products/{id} */
export function updateProductAPI(id: string, data: PmsProductParam) {
  const { skus: _skus, attribute_values: _attributeValues, ...payload } = mapProductPayload(data)
  return request<CommonResult<PmsProduct>>({
    url: '/admin/products/' + id,
    method: 'put',
    data: payload satisfies ProductUpdatePayload,
  })
}

/** 商品详情 —— GET /admin/products/{id} */
export function getProductAPI(id: string) {
  return request<CommonResult<ProductDetailResponse>>({
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

/** 添加 SKU —— POST /admin/products/{productId}/skus */
export function createProductSkuAPI(productId: string, sku: SkuStock) {
  return request<CommonResult<SkuStock>>({
    url: `/admin/products/${productId}/skus`,
    method: 'post',
    data: mapSkuPayload(sku),
  })
}

/** 编辑 SKU —— PUT /admin/products/{productId}/skus/{skuId} */
export function updateProductSkuAPI(productId: string, skuId: string, sku: SkuStock) {
  const payload = mapSkuPayload(sku)
  return request<CommonResult<SkuStock>>({
    url: `/admin/products/${productId}/skus/${skuId}`,
    method: 'put',
    data: {
      price: payload.price,
      promotion_price: payload.promotion_price,
      stock: payload.stock,
      pic: payload.pic,
      spec: payload.spec,
    },
  })
}

/** 删除 SKU —— DELETE /admin/products/{productId}/skus/{skuId} */
export function deleteProductSkuAPI(productId: string, skuId: string) {
  return request<CommonResult<null>>({
    url: `/admin/products/${productId}/skus/${skuId}`,
    method: 'delete',
  })
}

/** 全量更新商品属性值 */
export function updateProductAttributesAPI(
  productId: string,
  attributeValues: Record<string, string>,
) {
  return request<CommonResult<{ productId: string }>>({
    url: `/admin/products/${productId}/attributes`,
    method: 'put',
    data: attributeValues,
  })
}
