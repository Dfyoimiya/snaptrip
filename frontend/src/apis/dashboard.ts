import { getStatsOverviewAPI, getSalesStatsAPI, getProductRankAPI } from './stats'
import type { SalesStatItem, ProductRankItem, StatsOverview } from './stats'

export interface DashboardData {
  overview: StatsOverview | null
  salesStats: SalesStatItem[]
  productRank: ProductRankItem[]
}

/** 仪表盘聚合数据 —— 并行调用 3 个真实 API */
export async function getDashboardData(): Promise<DashboardData> {
  const [overviewRes, salesRes, rankRes] = await Promise.all([
    getStatsOverviewAPI(),
    getSalesStatsAPI(7),
    getProductRankAPI(10),
  ])
  return {
    overview: overviewRes.data,
    salesStats: salesRes.data || [],
    productRank: rankRes.data || [],
  }
}
