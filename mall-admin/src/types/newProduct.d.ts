/** 首页新品推荐 */
export interface SmsHomeNewProduct {
  id?: number
  productId?: number
  productName?: string
  recommendStatus?: number
  sort?: number
  createTime?: string
}

/** 新品推荐查询参数 */
export interface NewProductQueryParam {
  productName?: string
  recommendStatus?: number
  pageNum: number
  pageSize: number
}
