/**
 * ============================================
 * 会员 API
 * 登录、注册、获取用户信息等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { LoginResult, MemberInfo, LoginParam, RegisterParam } from '@/types/member'

/**
 * 用户登录
 * @param data 登录参数（邮箱+密码）
 */
export const loginAPI = (data: LoginParam) => {
  return post<LoginResult>('/api/v1/auth/login', data)
}

/**
 * 获取当前登录用户信息
 */
export const getMemberInfoAPI = () => {
  return get<MemberInfo>('/api/v1/auth/me')
}

/**
 * 用户注册
 * @param data 注册参数
 */
export const registerAPI = (data: RegisterParam) => {
  return post<LoginResult>('/api/v1/auth/register', data)
}

/**
 * 获取会员完整资料 (portal profile)
 */
export const getMemberProfileAPI = () => {
  return get<MemberInfo>('/api/v1/portal/member/profile')
}

/**
 * 刷新访问令牌
 */
export const refreshTokenAPI = (token: string) => {
  return post<LoginResult>('/api/v1/auth/refresh', { refresh_token: token })
}

/**
 * 登出（撤销 refresh token）
 */
export const logoutAPI = (token: string) => {
  return post<void>('/api/v1/auth/logout', { refresh_token: token })
}
