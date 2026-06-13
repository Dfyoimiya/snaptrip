import type { LoginForm } from '@/types'
import type { CommonResult } from '@/types/common'
import request from '@/utils/request'

/** 登录 —— POST /auth/login（前端 username 映射到后端 email） */
export function loginApi(data: LoginForm) {
  return request<CommonResult<{ access_token: string; refresh_token: string }>>({
    url: '/auth/login',
    method: 'post',
    data: {
      email: data.username,
      password: data.password,
    },
  })
}

/** 登出 —— POST /auth/logout */
export function logoutApi(refreshToken?: string) {
  return request<CommonResult<null>>({
    url: '/auth/logout',
    method: 'post',
    data: { refresh_token: refreshToken },
  })
}

/** 刷新令牌 —— POST /auth/refresh */
export function refreshTokenAPI(refreshToken: string) {
  return request<CommonResult<{ access_token: string; refresh_token: string }>>({
    url: '/auth/refresh',
    method: 'post',
    data: { refresh_token: refreshToken },
  })
}

/** 获取当前用户信息 —— GET /auth/me */
export function getUserInfoApi() {
  return request<CommonResult<{
    id: string
    email: string
    nickname: string | null
    avatar_url: string | null
  }>>({
    url: '/auth/me',
    method: 'get',
  })
}
