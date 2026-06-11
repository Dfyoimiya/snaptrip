/**
 * ============================================
 * 会员相关类型定义
 * 对应后端 UmsMember 及其关联 Schema
 * ============================================
 */

/** 登录请求参数 */
export interface LoginParam {
  /** 用户名 */
  username: string
  /** 密码 */
  password: string
}

/** 注册请求参数 */
export interface RegisterParam {
  /** 用户名 */
  username: string
  /** 密码 */
  password: string
  /** 手机号 */
  telephone: string
  /** 验证码 */
  authCode: string
}

/** 登录响应结果 */
export interface LoginResult {
  /** JWT Token */
  token: string
  /** Token 前缀 */
  tokenHead: string
  /** 会员信息 */
  memberInfo?: MemberInfo
}

/** 会员信息 */
export interface MemberInfo {
  /** 会员ID */
  id: number
  /** 会员等级ID */
  memberLevelId: number
  /** 用户名 */
  username: string
  /** 昵称 */
  nickname: string
  /** 手机号 */
  phone: string
  /** 头像 */
  icon: string
  /** 性别：0->未知；1->男；2->女 */
  gender: number
  /** 生日 */
  birthday: string
  /** 城市 */
  city: string
  /** 个性签名 */
  personalizedSignature: string
  /** 积分 */
  integration: number
  /** 成长值 */
  growth: number
  /** 会员登录次数 */
  loginCount: number
  /** 关注数量 */
  attentionCount: number
  /** 收藏数量 */
  collectProductCount: number
  /** 浏览记录数量 */
  readCount: number
  /** 优惠券数量 */
  couponCount: number
}
