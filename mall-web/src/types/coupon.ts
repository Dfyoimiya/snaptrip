/**
 * ============================================
 * 优惠券相关类型定义
 * 对应后端 SmsCoupon Schema (CouponResponse)
 * ============================================
 */

/** 优惠券信息 */
export interface SmsCoupon {
  /** ID */
  id: string
  /** 优惠券类型：0->全场赠券；1->会员赠券；2->购物赠券；3->注册赠券 */
  type: number
  /** 名称 */
  name: string
  /** 数量 */
  count: number
  /** 金额 */
  amount: number
  /** 每人限领张数 */
  perLimit: number
  /** 使用门槛；0表示无门槛 */
  minAmount: number
  /** 开始时间 */
  startTime: string
  /** 结束时间 */
  endTime: string
  /** 使用类型：0->全场通用；1->指定分类；2->指定商品 */
  useType: number
  /** 发行数量 */
  publishCount: number
  /** 已领取数量 */
  receiveCount: number
  /** 已使用数量 */
  useCount: number
  /** 状态 */
  status: number
  /** 优惠券编码 */
  code?: string | null
  /** 备注 */
  note?: string | null
  /** 指定分类ID */
  categoryId?: string | null
  /** 指定品牌ID */
  brandId?: string | null
  /** 创建时间 */
  createdAt: string
  /** 更新时间 */
  updatedAt?: string | null
}
