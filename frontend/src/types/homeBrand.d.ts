/**
 * 首页品牌推荐
 */
export interface SmsHomeBrand {
  id?: string
  brandId?: string
  brandName?: string
  recommendStatus?: number // 0->不推荐 1->推荐
  sort?: number
  createdAt?: string
}

