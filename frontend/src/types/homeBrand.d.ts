/**
 * 首页品牌推荐
 */
export interface SmsHomeBrand {
  id?: number
  brandId?: number
  brandName?: string
  recommendStatus?: number // 0->不推荐 1->推荐
  sort?: number
  createTime?: string
}


