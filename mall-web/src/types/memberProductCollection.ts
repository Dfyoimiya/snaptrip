/**
 * ============================================
 * 会员商品收藏类型定义
 * 对应原项目 types/memberProductCollection.d.ts
 * ============================================
 */

/** 会员商品收藏 - 对应后端 MemberProductCollection Schema */
export interface MemberProductCollection {
  /** ID */
  id?: string
  /** 创建时间 */
  createdAt?: string
  /** 商品ID */
  productId: string
  /** 商品名称 */
  productName: string
  /** 商品图片 */
  productPic: string
  /** 商品价格 */
  productPrice: number
}
