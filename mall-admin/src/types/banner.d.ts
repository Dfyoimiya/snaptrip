/**
 * 首页轮播广告
 */
export interface SmsHomeAdvertise {
  id?: number
  name?: string
  type?: number // 0->PC 1->APP
  pic?: string
  startTime?: string
  endTime?: string
  status?: number // 0->下线 1->上线
  clickCount?: number
  orderCount?: number
  url?: string
  note?: string
  sort?: number
  createTime?: string
}
