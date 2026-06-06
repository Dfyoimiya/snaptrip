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
export * from './companyAddress'
export * from './admin'
export * from './role'
export * from './resource'
export * from './orderSetting'
export * from './coupon'

/** 登录表单 */
export interface LoginForm {
  username: string
  password: string
}

/** 菜单项（来自后端权限） */
export interface MenuItem {
  id: number
  parentId: number
  title: string
  name: string
  icon?: string
  sort?: number
  hidden?: number
}

/** 用户信息（含权限） */
export interface UserInfo {
  username: string
  nickname: string
  avatar: string
  token: string
  menus: MenuItem[]
  roles: string[]
}
