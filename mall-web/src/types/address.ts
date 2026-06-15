/**
 * ============================================
 * 收货地址相关类型定义
 * 对应后端 UmsMemberReceiveAddress 类型
 * ============================================
 */

/** 会员收货地址 */
export interface MemberReceiveAddress {
  /** 地址ID */
  id?: number
  /** 收货人名称 */
  name: string
  /** 手机号码 */
  phone: string
  /** 是否为默认（0-否 1-是） */
  defaultStatus?: number
  /** 邮政编码 */
  postCode?: string
  /** 省份/直辖市 */
  province?: string
  /** 城市 */
  city?: string
  /** 区 */
  region?: string
  /** 详细地址(街道) */
  detailAddress?: string
}
