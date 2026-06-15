/** 优惠券 */
export interface SmsCoupon {
  id?: string
  type?: number
  name?: string
  platform?: number
  count?: number
  amount?: number
  perLimit?: number
  minAmount?: number
  startTime?: string
  endTime?: string
  useType?: number
  note?: string
  publishCount?: number
  useCount?: number
  receiveCount?: number
  enableTime?: string
  code?: string
  memberLevel?: number
}

/** 优惠券扩展（含关联商品/分类） */
export interface SmsCouponExt extends SmsCoupon {
  productRelationList?: CouponProductRelation[]
  productCategoryRelationList?: CouponProductCategoryRelation[]
}

/** 优惠券与商品关联 */
export interface CouponProductRelation {
  couponId?: string
  productId?: string
  productName?: string
  productSn?: string
}

/** 优惠券与商品分类关联 */
export interface CouponProductCategoryRelation {
  couponId?: string
  categoryId?: string
  productCategoryName?: string
  parentCategoryName?: string
}

/** 优惠券查询参数 */
export interface CouponQueryParam {
  name?: string
  type?: number
  page: number
  page_size: number
}

/** 优惠券商品选择项 */
export interface CouponSelectProductOptionVo {
  productId?: string
  productName?: string
  productSn?: string
}

/** 优惠券领取记录查询参数 */
export interface CouponHistoryQueryParam {
  couponId?: string
  useStatus?: number
  orderSn?: string
  page: number
  page_size: number
}
