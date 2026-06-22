/**
 * ============================================
 * 共享类型导出
 * ============================================
 */

export type { CommonResult, CommonPage, PageParam, ApiResult } from './common'
export type { MemberInfo, LoginParam, RegisterParam, LoginResult } from './member'
export type {
  PmsProduct,
  PmsProductCategory,
  CategoryTreeNode,
  ProductListParam,
  PmsProductAttribute,
  PmsProductAttributeValue,
  PmsSkuStock,
  PmsProductFullReduction,
  PmsProductLadder,
  PmsPortalProductDetail,
  SpecOption,
  ServiceItem,
  ShareItem,
} from './product'
export type { MemberReceiveAddress } from './address'
export type { PmsBrand } from './brand'
export type { SmsCoupon } from './coupon'
export type { CartItem } from './cart'
export type { OmsOrderItem, OmsOrderDetail, OrderParam } from './order'
export type { HomeContentResult, HomeFlashPromotion } from './home'
export type { MemberProductCollection } from './memberProductCollection'

// ─── 前端专用工具类型 ──────────────────────────────────────

/** 商品摘要（用于对比、浏览足迹等场景） */
export interface ProductSummary {
  id: string | number
  name: string
  price: number
  image: string
  brand?: string
}
