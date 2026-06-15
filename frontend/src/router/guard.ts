import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { ElMessage } from 'element-plus'
import { getToken, getRefreshToken, clearAuth } from '@/utils/storage'
import { isTokenExpired } from '@/utils/jwt'
import { refreshAccessToken } from '@/utils/tokenRefresh'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login', '/404']

export function setupRouterGuard(router: Router) {
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
            permissionStore.generateRoutes(userStore.userInfo.menus)
            permissionStore.addRouters.forEach((route) => {
              router.addRoute(route as any)
            })
            router.addRoute({
              path: '/redirect/:path(.*)',
              component: () => import('@/views/layout/components/Redirect.vue'),
            } as any)

            next({ ...to, replace: true })
          } catch (error) {
            console.error('动态路由生成失败:', error)
            ElMessage.error('路由初始化失败')
            await userStore.logout()
            next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
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
                permissionStore.generateRoutes(userStore.userInfo.menus)
                permissionStore.addRouters.forEach((route) => {
                  router.addRoute(route as any)
                })
                router.addRoute({
                  path: '/redirect/:path(.*)',
                  component: () => import('@/views/layout/components/Redirect.vue'),
                } as any)
                next({ ...to, replace: true })
              } catch (error) {
                console.error('动态路由生成失败:', error)
                clearAuth()
                next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
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
        next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
      }
      NProgress.done()
      return
    }

    // 3. 未登录
    if (whiteList.includes(to.path)) {
      next()
    } else {
      next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
      NProgress.done()
    }
  })

  router.afterEach(() => {
    NProgress.done()
  })
}
