import type { CommonResult } from '@/types/common'
import request from '@/utils/request'

export interface SalesStatItem {
  date?: string
  orderCount?: number
  amount?: number
}

export interface ProductRankItem {
  productId?: string
  productName?: string
  saleCount?: number
  amount?: number
}

export interface StatsOverview {
  todayOrderCount?: number
  todaySalesAmount?: number
  todayNewMemberCount?: number
  totalProductCount?: number
  onShelfProductCount?: number
}

/** 仪表盘概览 —— GET /admin/stats/overview */
export function getStatsOverviewAPI() {
  return request<CommonResult<StatsOverview>>({
    url: '/admin/stats/overview',
    method: 'get',
  })
}

/** 销售趋势 —— GET /admin/stats/sales?days=7 */
export function getSalesStatsAPI(days: number = 7) {
  return request<CommonResult<SalesStatItem[]>>({
    url: '/admin/stats/sales',
    method: 'get',
    params: { days },
  })
}

/** 商品销量排行 —— GET /admin/stats/products?limit=10 */
export function getProductRankAPI(limit: number = 10) {
  return request<CommonResult<ProductRankItem[]>>({
    url: '/admin/stats/products',
    method: 'get',
    params: { limit },
  })
}
