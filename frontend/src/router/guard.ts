import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { ElMessage } from 'element-plus'
import { getToken, getRefreshToken, setToken, setRefreshToken, clearAuth } from '@/utils/storage'
import { isTokenExpired } from '@/utils/jwt'
import axios from 'axios'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login', '/404']

/** 尝试用 refresh_token 换取新的 access_token（不依赖 Pinia store） */
async function trySilentRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 10000 },
    )
    const res = response.data
    if (res.code === 0 && res.data) {
      setToken(res.data.access_token)
      setRefreshToken(res.data.refresh_token)
      return true
    }
    return false
  } catch {
    return false
  }
}

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
              path: '/:pathMatch(.*)*',
              redirect: '/404',
              hidden: true,
            } as any)
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
      // 尝试静默刷新
      const refreshed = await trySilentRefresh()
      if (refreshed) {
        // 刷新成功，同步 store 中的 token
        userStore.userInfo.token = getToken() || ''
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
                path: '/:pathMatch(.*)*',
                redirect: '/404',
                hidden: true,
              } as any)
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
