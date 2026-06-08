import request from '@/utils/request'

export interface DashboardData {
  today_orders: number
  today_revenue: number
  today_revenue_display: string
  pending_returns: number
  new_members: number
  order_status_counts: { label: string; count: number; type: string }[]
  top_products: { name: string; sales: number; amount: number }[]
  week_days: string[]
  week_sales: number[]
  latest_orders: { id: number; orderSn: string; member: string; amount: number; status: number; statusLabel: string }[]
}

export function getDashboardData() {
  return request<DashboardData>({
    url: '/admin/dashboard',
    method: 'get',
  })
}
