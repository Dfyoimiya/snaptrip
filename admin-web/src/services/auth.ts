import request from '@/utils/request';

export const loginAPI = (data: API.LoginRequest) =>
  request.post<API.ApiResponse<API.LoginResponse>>('/auth/login', data);

export const refreshTokenAPI = (refreshToken: string) =>
  request.post<API.ApiResponse<API.LoginResponse>>('/auth/refresh', { refresh_token: refreshToken });

export const getAdminInfoAPI = () =>
  request.get<API.ApiResponse<API.CurrentUser>>('/auth/me');
