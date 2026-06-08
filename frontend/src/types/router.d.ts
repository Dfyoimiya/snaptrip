import type { RouteRecordRaw } from 'vue-router'

/** 路由元信息扩展 */
export interface RouteMetaExt {
  /** 页面标题 */
  title: string
  /** 菜单图标 */
  icon?: string
  /** 是否隐藏菜单 */
  hidden?: boolean
  /** 是否始终显示根菜单 */
  alwaysShow?: boolean
  /** 是否需要认证 */
  requiresAuth?: boolean
  /** 菜单排序 */
  sort?: number
  /** 缓存页面 */
  keepAlive?: boolean
}

/** vue-router 路由扩展 */
export type RouteRecordExt = RouteRecordRaw & {
  /** 前端隐藏 */
  hidden?: boolean
  /** 前端排序 */
  sort?: number
  /** 下级子路由 */
  children?: RouteRecordExt[]
  /** 是否永远显示 */
  alwaysShow?: boolean
  /** 路由元信息 */
  meta?: RouteMetaExt
}
