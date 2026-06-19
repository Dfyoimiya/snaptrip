export * from './menu'
export * from './router'
export * from './common'
export * from './product'
export * from './brand'
export * from './productCate'
export * from './productAttr'
export * from './order'
export * from './returnApply'
export * from './returnReason'
export * from './admin'
export * from './role'
export * from './resource'
export * from './orderSetting'
export * from './coupon'

/** Swagger: LoginRequest */
export interface ILoginParams {
  email: string
  password: string
}

/** 登录表单（页面模型） */
export interface LoginForm {
  username: string
  password: string
}

/** Swagger: TokenResponse */
export interface ILoginResponse {
  accessToken: string
  refreshToken: string
  tokenType: string
}

/** Swagger: UserMeResponse */
export interface IUser {
  id: string
  email: string
  nickname: string | null
  avatarUrl: string | null
  gender: number | null
}

/** 菜单项（来自后端权限） */
export interface MenuItem {
  id: string
  parentId: string | null
  title: string
  name: string | null
  icon?: string
  sort?: number
  hidden?: number
}

/** Swagger: UserAccessResponse */
export interface IUserAccess {
  roles: string[]
  permissions: string[]
  menus: MenuItem[]
}

/** 用户信息（含权限） */
export interface UserInfo {
  id: string
  username: string
  nickname: string
  avatar: string
  token: string
  menus: MenuItem[]
  roles: string[]
  permissions: string[]
}
