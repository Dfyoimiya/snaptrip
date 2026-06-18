import type { Component, RouteLocationRaw } from 'vue-router'

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

/** 项目内部路由描述。注册到 vue-router 时统一转换，避免与其联合类型发生交叉冲突。 */
export interface RouteRecordExt {
  path: string
  name?: string
  component?: Component | (() => Promise<unknown>)
  redirect?: RouteLocationRaw
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
