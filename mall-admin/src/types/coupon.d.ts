/** 优惠券 */
export interface SmsCoupon {
  id?: number
  type?: number
  name?: string
  platform?: number
  count?: number
  amount?: number
  perLimit?: number
  minPoint?: number
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
  couponId?: number
  productId?: number
  productName?: string
  productSn?: string
}

/** 优惠券与商品分类关联 */
export interface CouponProductCategoryRelation {
  couponId?: number
  productCategoryId?: number
  productCategoryName?: string
  parentCategoryName?: string
}

/** 优惠券查询参数 */
export interface CouponQueryParam {
  name?: string
  type?: number
  pageNum: number
  pageSize: number
}

/** 优惠券商品选择项 */
export interface CouponSelectProductOptionVo {
  productId?: number
  productName?: string
  productSn?: string
}

/** 优惠券领取记录查询参数 */
export interface CouponHistoryQueryParam {
  couponId?: number
  useStatus?: number
  orderSn?: string
  pageNum: number
  pageSize: number
}
