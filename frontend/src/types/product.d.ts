/** 商品 */
export interface PmsProduct {
  id?: number
  brandId: number
  brandName?: string
  productCategoryId: number
  productCategoryName?: string
  productAttributeCategoryId?: number
  name: string
  pic: string
  productSn: string
  deleteStatus?: number
  publishStatus?: number
  newStatus?: number
  recommandStatus?: number
  verifyStatus?: number
  sort?: number
  sale?: number
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
}

/** 商品查询参数 */
export interface ProductQueryParam extends PageParam {
  publishStatus?: number
  verifyStatus?: number
  productSn?: string
  productCategoryId?: number
  brandId?: number
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
  id?: number
  productId?: number
  productAttributeId: number
  value: string
}

/** SKU库存 */
export interface SkuStock {
  id?: number
  productId?: number
  skuCode?: string
  price?: number
  stock?: number
  lowStock?: number
  pic?: string
  sale?: number
  promotionPrice?: number
  lockStock?: number
  spData?: string
}

/** 商品参数值 */
export interface ProductParamValue {
  id?: number
  productId?: number
  productAttributeId: number
  value: string
}
