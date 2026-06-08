import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { asyncRouterMap, constantRouterMap } from '@/router'
import type { RouteRecordExt, MenuItem } from '@/types'
import type { RouteRecordNormalized } from 'vue-router'

/**
 * 判断路由是否有权限
 * 根据后端返回的菜单列表，检查当前路由是否在权限列表中
 */
function hasPermission(menus: MenuItem[], route: RouteRecordExt): boolean {
  if (route.name) {
    const currMenu = menus.find(menu => menu.name === route.name)
    if (currMenu) {
      // 动态更新路由的标题、图标和可见性
      if (currMenu.title) {
        if (!route.meta) route.meta = { title: '' }
        route.meta.title = currMenu.title
      }
      if (currMenu.icon) {
        if (!route.meta) route.meta = { title: '' }
        route.meta.icon = currMenu.icon
      }
      route.hidden = currMenu.hidden !== 0
      route.sort = currMenu.sort
      return true
    } else {
      route.sort = 0
      // 对于隐藏的路由（如详情页），如果没有在菜单中但标记了 hidden，仍然允许访问
      if (route.hidden === true) {
        route.sort = -1
        return true
      }
      return false
    }
  }
  // 没有 name 的路由默认允许
  return true
}

/** 递归过滤有权限的路由 */
function filterAsyncRoutes(routes: RouteRecordExt[], menus: MenuItem[]): RouteRecordExt[] {
  const res: RouteRecordExt[] = []

  routes.forEach(route => {
    const tmp = { ...route }
    if (hasPermission(menus, tmp)) {
      if (tmp.children) {
        tmp.children = filterAsyncRoutes(tmp.children, menus)
      }
      res.push(tmp)
    }
  })

  return res
}

/** 路由排序（降序） */
function sortRouters(routes: RouteRecordExt[]) {
  routes.forEach(route => {
    if (route.children && route.children.length > 0) {
      route.children.sort(compareRoutes)
    }
  })
  routes.sort(compareRoutes)
}

function compareRoutes(a: RouteRecordExt, b: RouteRecordExt): number {
  const sortA = a.sort ?? 0
  const sortB = b.sort ?? 0
  return sortB - sortA
}

export const usePermissionStore = defineStore('permission', () => {
  // State
  const routers = shallowRef<RouteRecordExt[]>([...constantRouterMap])
  const addRouters = shallowRef<RouteRecordExt[]>([])
  const sidebarRouters = ref<RouteRecordNormalized[]>([])

  // Actions
  /** 根据用户菜单生成可访问路由 */
  function generateRoutes(menus: MenuItem[]) {
    const accessedRoutes = filterAsyncRoutes([...asyncRouterMap], menus)
    sortRouters(accessedRoutes)
    addRouters.value = accessedRoutes
    routers.value = [...constantRouterMap, ...accessedRoutes]
  }

  /** 设置侧边栏路由 */
  function setSidebarRouters(routes: RouteRecordNormalized[]) {
    sidebarRouters.value = routes
  }

  /** 重置权限 */
  function resetPermission() {
    routers.value = [...constantRouterMap]
    addRouters.value = []
    sidebarRouters.value = []
  }

  return {
    routers,
    addRouters,
    sidebarRouters,
    generateRoutes,
    setSidebarRouters,
    resetPermission,
  }
})
