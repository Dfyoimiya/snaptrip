/**
 * 秒杀活动
 */
export interface SmsFlashPromotion {
  id?: string
  title?: string
  startDate?: string
  endDate?: string
  status?: number // 0->下线 1->上线
  createdAt?: string
}

/**
 * 秒杀活动时段
 */
export interface SmsFlashPromotionSession {
  id?: string
  name?: string
  startTime?: string
  endTime?: string
  status?: number // 0->下线 1->上线
  createdAt?: string
}

/**
 * 秒杀活动商品 —— 匹配后端 FlashProductResponse
 */
export interface SmsFlashPromotionProduct {
  id?: string
  /** API返回: session_id → sessionId */
  sessionId?: string
  /** 表单用: 活动ID */
  flashPromotionId?: string
  /** 表单用: 时段ID */
  flashPromotionSessionId?: string
  productId?: string
  productName?: string
  productPic?: string
  skuId?: string
  productPrice?: number
  /** API返回: flash_price → flashPrice */
  flashPrice?: number
  /** 表单别名: flashPrice */
  flashPromotionPrice?: number
  /** API返回: flash_stock → flashStock */
  flashStock?: number
  /** 表单别名: flashStock */
  flashPromotionCount?: number
  /** API返回: flash_limit → flashLimit */
  flashLimit?: number
  /** 表单别名: flashLimit */
  flashPromotionLimit?: number
  sort?: number
  /** 商品属性（关联商品） */
  productAttr?: string
  createdAt?: string
}

/** 秒杀活动与商品关联 */
export interface SmsFlashPromotionProductRelation {
  id?: string
  flashPromotionId?: string
  flashPromotionSessionId?: string
  productId?: string
  productName?: string
  productPrice?: number
  flashPromotionPrice?: number
  flashPromotionCount?: number
  flashPromotionLimit?: number
  sort?: number
}

/** 秒杀商品查询参数 */
export interface FlashProductQueryParam {
  flashPromotionId: string
  flashPromotionSessionId: string
  page: number
  page_size: number
}

/**
 * 秒杀活动与时段关联关系（用于选择）
 */
export interface FlashPromotionRelation {
  flashPromotionId?: string
  flashPromotionTitle?: string
  flashPromotionSessionId?: string
  flashPromotionSessionName?: string
}
