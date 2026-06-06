/** 首页人气推荐 */
export interface SmsHomeRecommendProduct {
  id?: number
  productId?: number
  productName?: string
  recommendStatus?: number
  sort?: number
  createTime?: string
}

/** 人气推荐查询参数 */
export interface RecommendProductQueryParam {
  productName?: string
  recommendStatus?: number
  pageNum: number
  pageSize: number
}
