import type {
  ILoginParams,
  ILoginResponse,
  IUser,
  IUserAccess,
  LoginForm,
} from '@/types'
import type { CommonResult } from '@/types/common'
import request from '@/utils/request'

/** 登录 —— POST /auth/login（前端 username 映射到后端 email） */
export function loginApi(data: LoginForm) {
  const params: ILoginParams = {
    email: data.username,
    password: data.password,
  }
  return request<CommonResult<ILoginResponse>>({
    url: '/auth/login',
    method: 'post',
    data: params,
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
  return request<CommonResult<ILoginResponse>>({
    url: '/auth/refresh',
    method: 'post',
    data: { refresh_token: refreshToken },
  })
}

/** 获取当前用户信息 —— GET /auth/me */
export function getUserInfoApi() {
  return request<CommonResult<IUser>>({
    url: '/auth/me',
    method: 'get',
  })
}

/** 获取当前后台用户的 RBAC 菜单与按钮权限 */
export function getUserAccessApi() {
  return request<CommonResult<IUserAccess>>({
    url: '/auth/access',
    method: 'get',
  })
}
