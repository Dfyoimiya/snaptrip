import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { constantRouterMap, notFoundRoute } from '@/router'

vi.mock('@/views/layout/Layout.vue', () => ({
  default: { template: '<router-view />' },
}))

describe('dynamic route initialization order', () => {
  it('does not register the 404 fallback before permission routes', () => {
    expect(constantRouterMap.some(route => route.name === 'notFoundFallback')).toBe(false)
    expect(notFoundRoute.name).toBe('notFoundFallback')
  })

  it('matches a permission route after it is added before the fallback', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: constantRouterMap as any,
    })

    router.addRoute({
      path: '/pms',
      name: 'testPms',
      component: { template: '<div />' },
      children: [
        {
          path: 'productCate',
          name: 'testProductCate',
          component: { template: '<div />' },
        },
      ],
    })
    router.addRoute(notFoundRoute as any)

    await router.push('/pms/productCate')

    expect(router.currentRoute.value.name).toBe('testProductCate')
    expect(router.currentRoute.value.path).toBe('/pms/productCate')
  })
})
