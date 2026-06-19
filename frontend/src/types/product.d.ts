import type { PageParam } from './common'

/** 商品 */
export interface PmsProduct {
  id?: string
  brandId: string
  brandName?: string
  categoryId: string
  productCategoryName?: string
  productAttributeCategoryId?: string
  name: string
  defaultPic: string
  productSn: string
  deleteStatus?: number
  publishStatus?: number
  newStatus?: number
  recommendStatus?: number
  verifyStatus?: number
  saleCount?: number
  price: number
  promotionPrice?: number
  giftGrowth?: number
  giftPoint?: number
  usePointLimit?: number
  subTitle: string
  originalPrice?: number
  stock?: number
  lowStock?: number
  unit?: string
  weight?: number
  previewStatus?: number
  serviceIds?: string
  description?: string
  freightTemplateId?: string
  keywords?: string
  note?: string
  albumPics?: string
  detailTitle?: string
  detailDesc?: string
  detailHtml?: string
  detailMobileHtml?: string
  promotionStartTime?: string
  promotionEndTime?: string
  promotionPerLimit?: number
  promotionType?: number
  brandNameCn?: string
  productCategoryNameCn?: string
  /** 排序 */
  sort?: number
}

/** 商品查询参数 */
export interface ProductQueryParam extends PageParam {
  keyword?: string
  publishStatus?: number
  verifyStatus?: number
  productSn?: string
  categoryId?: string
  brandId?: string
}

/** 商品参数（创建/更新） */
export interface PmsProductParam extends PmsProduct {
  // 商品属性相关
  productAttributeValueList?: ProductAttrValue[]
  // SKU库存相关
  skuStockList?: SkuStock[]
  // 商品参数相关
  productParamValueList?: ProductParamValue[]
}

/** FastAPI 商品详情响应 */
export interface ProductDetailResponse extends PmsProduct {
  categoryName?: string
  skus: Array<SkuStock & { pic?: string }>
  attributeValues: Array<{
    attributeId: string
    value: string
  }>
}

/** FastAPI 商品创建请求体 */
export interface ProductCreatePayload {
  name: string
  sub_title?: string | null
  brand_id?: string | null
  category_id?: string | null
  product_sn?: string | null
  price: number
  original_price?: number | null
  promotion_price?: number | null
  promotion_start_time?: string | null
  promotion_end_time?: string | null
  promotion_per_limit?: number
  promotion_type?: number
  publish_status?: number
  new_status?: number
  recommend_status?: number
  description?: string | null
  keywords?: string | null
  unit?: string | null
  weight?: number | null
  service_ids?: string | null
  freight_template_id?: string | null
  pics?: string | null
  album_pics?: string | null
  default_pic?: string | null
  skus: ProductSkuPayload[]
  attribute_values: Record<string, string>
}

/** FastAPI 商品编辑请求体 */
export type ProductUpdatePayload = Omit<ProductCreatePayload, 'skus' | 'attribute_values'>

/** FastAPI SKU 请求体 */
export interface ProductSkuPayload {
  sku_code: string
  spec: string
  price: number
  promotion_price?: number | null
  stock: number
  low_stock: number
  pic?: string | null
}

/** 商品属性值 */
export interface ProductAttrValue {
  id?: string
  productId?: string
  productAttributeId: string
  value: string
}

/** SKU库存 */
export interface SkuStock {
  id?: string
  productId?: string
  skuCode?: string
  price?: number
  stock?: number
  lowStock?: number
  defaultPic?: string
  saleCount?: number
  promotionPrice?: number
  lockStock?: number
  spec?: string
  spData?: string
}

/** 商品参数值 */
export interface ProductParamValue {
  id?: string
  productId?: string
  productAttributeId: string
  value: string
}
