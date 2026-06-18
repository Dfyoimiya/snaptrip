import request from '@/utils/request';

export const getDashboardAPI = () =>
  request.get<API.ApiResponse<API.DashboardData>>('/admin/dashboard');

export const getStatsOverviewAPI = () =>
  request.get<API.ApiResponse<API.StatsOverview>>('/admin/stats/overview');

export const getSalesStatsAPI = (days: number = 7) =>
  request.get<API.ApiResponse<API.SalesStatItem[]>>('/admin/stats/sales', { params: { days } });

export const getProductRankAPI = (limit: number = 10) =>
  request.get<API.ApiResponse<API.ProductRankItem[]>>('/admin/stats/products', { params: { limit } });
