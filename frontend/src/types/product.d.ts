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
}

/** 商品参数值 */
export interface ProductParamValue {
  id?: string
  productId?: string
  productAttributeId: string
  value: string
}
