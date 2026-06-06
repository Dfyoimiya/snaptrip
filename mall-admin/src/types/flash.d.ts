/**
 * 秒杀活动
 */
export interface SmsFlashPromotion {
  id?: number
  title?: string
  startDate?: string
  endDate?: string
  status?: number // 0->下线 1->上线
  createTime?: string
}

/**
 * 秒杀活动时段
 */
export interface SmsFlashPromotionSession {
  id?: number
  name?: string
  startTime?: string
  endTime?: string
  status?: number // 0->下线 1->上线
  createTime?: string
}

/**
 * 秒杀活动商品
 */
export interface SmsFlashPromotionProduct {
  id?: number
  flashPromotionId?: number
  flashPromotionSessionId?: number
  productId?: number
  productName?: string
  productPic?: string
  productPrice?: number
  productAttr?: string
  flashPromotionPrice?: number
  flashPromotionCount?: number
  flashPromotionLimit?: number
  sort?: number
  createTime?: string
}

/** 秒杀活动与商品关联 */
export interface SmsFlashPromotionProductRelation {
  id?: number
  flashPromotionId?: number
  flashPromotionSessionId?: number
  productId?: number
  productName?: string
  productPrice?: number
  flashPromotionPrice?: number
  flashPromotionCount?: number
  flashPromotionLimit?: number
  sort?: number
}

/** 秒杀商品查询参数 */
export interface FlashProductQueryParam {
  flashPromotionId: number
  flashPromotionSessionId: number
  pageNum: number
  pageSize: number
}

/**
 * 秒杀活动与时段关联关系（用于选择）
 */
export interface FlashPromotionRelation {
  flashPromotionId?: number
  flashPromotionTitle?: string
  flashPromotionSessionId?: number
  flashPromotionSessionName?: string
}
