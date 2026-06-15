/**
 * ============================================
 * 会员相关类型定义
 * 对应后端 User / UserMeResponse / TokenResponse
 * ============================================
 */

/** 登录请求参数 */
export interface LoginParam {
  /** 邮箱 */
  email: string
  /** 密码 */
  password: string
}

/** 注册请求参数 */
export interface RegisterParam {
  /** 邮箱 */
  email: string
  /** 密码 */
  password: string
}

/** 登录响应结果 (后端 TokenResponse, 经 deepConvertKeys 转换) */
export interface LoginResult {
  /** JWT Access Token */
  accessToken: string
  /** 刷新 Token */
  refreshToken: string
  /** Token 类型 */
  tokenType: string
}

/** 会员信息 (后端 UserMeResponse + portal profile, 经 deepConvertKeys 转换) */
export interface MemberInfo {
  /** 用户ID */
  id: string
  /** 邮箱 */
  email: string
  /** 昵称 */
  nickname: string
  /** 头像 URL */
  avatarUrl: string
}
