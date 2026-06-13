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
 * @param data 登录参数（用户名+密码）
 */
export const loginAPI = (data: LoginParam) => {
  return post<LoginResult>('/sso/login', data, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
    },
  })
}

/**
 * 获取当前登录用户信息
 */
export const getMemberInfoAPI = () => {
  return get<MemberInfo>('/sso/info')
}

/**
 * 用户注册
 * @param data 注册参数
 */
export const registerAPI = (data: RegisterParam) => {
  return post<unknown>('/sso/register', data, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
    },
  })
}

/**
 * 获取手机验证码
 * @param telephone 手机号
 */
export const getAuthCodeAPI = (telephone: string) => {
  return get<unknown>('/sso/getAuthCode', { telephone })
}
