import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { ElMessage } from 'element-plus'
import { getToken, getRefreshToken, clearAuth } from '@/utils/storage'
import { isTokenExpired } from '@/utils/jwt'
import { refreshAccessToken } from '@/utils/tokenRefresh'
import { notFoundRoute } from '@/router'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login', '/403', '/404']
const REDIRECT_ROUTE_NAME = 'runtimeRedirect'
const NOT_FOUND_ROUTE_NAME = 'notFoundFallback'

function getLoginRedirect(fullPath: string): string {
  const blockedPaths = ['/login', '/403', '/404']
  const redirect = blockedPaths.some(
    (path) => fullPath === path || fullPath.startsWith(`${path}?`),
  )
    ? '/'
    : fullPath
  return `/login?redirect=${encodeURIComponent(redirect)}`
}

export function setupRouterGuard(router: Router) {
  function registerRuntimeRoutes(permissionStore: ReturnType<typeof usePermissionStore>) {
    permissionStore.addRouters.forEach((route) => {
      if (!route.name || !router.hasRoute(route.name)) {
        router.addRoute(route as any)
      }
    })

    if (!router.hasRoute(REDIRECT_ROUTE_NAME)) {
      router.addRoute({
        path: '/redirect/:path(.*)',
        name: REDIRECT_ROUTE_NAME,
        component: () => import('@/views/layout/components/Redirect.vue'),
      } as any)
    }

    // 必须最后注册，确保刷新动态页面时先匹配刚添加的权限路由。
    if (!router.hasRoute(NOT_FOUND_ROUTE_NAME)) {
      router.addRoute(notFoundRoute as any)
    }
  }

  router.beforeEach(async (to, from, next) => {
    NProgress.start()

    const userStore = useUserStore()
    const permissionStore = usePermissionStore()

    // 1. 已登录但 access token 过期 → 尝试静默刷新
    if (userStore.isLoggedIn) {
      if (to.path === '/login') {
        next({ path: '/' })
        NProgress.done()
      } else {
        if (permissionStore.addRouters.length === 0) {
          try {
            if (userStore.userInfo.menus.length === 0) {
              await userStore.loadProfileAndAccess()
            }
            permissionStore.generateRoutes(userStore.userInfo.menus)
            registerRuntimeRoutes(permissionStore)

            next({ ...to, replace: true })
          } catch (error) {
            console.error('动态路由生成失败:', error)
            ElMessage.error('路由初始化失败')
            await userStore.logout()
            next(getLoginRedirect(to.fullPath))
            NProgress.done()
          }
        } else {
          next()
        }
      }
      return
    }

    // 2. access token 过期/不存在，但可能有 refresh token
    const currentToken = getToken()
    if (currentToken && isTokenExpired(currentToken) && getRefreshToken()) {
      // 尝试静默刷新（refreshAccessToken 内部保证并发安全）
      try {
        await refreshAccessToken()
        const newToken = getToken()
        if (newToken) {
          // 刷新成功，同步 store 中的 token
          userStore.userInfo.token = newToken
          // 重新进入守卫逻辑
          if (to.path === '/login') {
            next({ path: '/' })
          } else {
            if (permissionStore.addRouters.length === 0) {
              try {
                if (userStore.userInfo.menus.length === 0) {
                  await userStore.loadProfileAndAccess()
                }
                permissionStore.generateRoutes(userStore.userInfo.menus)
                registerRuntimeRoutes(permissionStore)
                next({ ...to, replace: true })
              } catch (error) {
                console.error('动态路由生成失败:', error)
                clearAuth()
                next(getLoginRedirect(to.fullPath))
              }
            } else {
              next()
            }
          }
          NProgress.done()
          return
        }
      } catch {
        // 刷新失败 → 清除并跳转登录
      }
      // 刷新失败 → 清除并跳转登录
      clearAuth()
      userStore.userInfo.token = ''
      if (whiteList.includes(to.path)) {
        next()
      } else {
        next(getLoginRedirect(to.fullPath))
      }
      NProgress.done()
      return
    }

    // 3. 未登录
    if (whiteList.includes(to.path)) {
      next()
    } else {
      next(getLoginRedirect(to.fullPath))
      NProgress.done()
    }
  })

  router.afterEach(() => {
    NProgress.done()
  })
}
