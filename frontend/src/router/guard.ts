import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { ElMessage } from 'element-plus'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login', '/404']

export function setupRouterGuard(router: Router) {
  router.beforeEach(async (to, from, next) => {
    NProgress.start()

    const userStore = useUserStore()
    const permissionStore = usePermissionStore()

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
            // 404 fallback
            router.addRoute({
              path: '/:pathMatch(.*)*',
              redirect: '/404',
              hidden: true,
            } as any)
            // redirect for refresh
            router.addRoute({
              path: '/redirect/:path(.*)',
              component: () => import('@/views/layout/components/Redirect.vue'),
            } as any)

            next({ ...to, replace: true })
          } catch (error) {
            console.error('动态路由生成失败:', error)
            ElMessage.error('路由初始化失败')
            await userStore.logout()
            next(`/login?redirect=${to.path}`)
            NProgress.done()
          }
        } else {
          next()
        }
      }
    } else {
      if (whiteList.includes(to.path)) {
        next()
      } else {
        next(`/login?redirect=${to.path}`)
        NProgress.done()
      }
    }
  })

  router.afterEach(() => {
    NProgress.done()
  })
}
