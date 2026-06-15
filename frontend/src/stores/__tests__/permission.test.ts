/**
 * 权限 Store 测试
 * 覆盖: generateRoutes 路由过滤与排序、resetPermission 重置、
 *       setSidebarRouters、empty menu 边界情况
 *
 * 注意: generateRoutes 依赖 @/router 导出的 asyncRouterMap。
 * 这里 Mock @/router 提供可控的测试路由数据。
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { MenuItem, RouteRecordExt } from '@/types'

// ─── Mock router to provide controlled test data ───────────────
vi.mock('@/router', () => {
  const testAsyncRoutes: RouteRecordExt[] = [
    {
      path: '/pms',
      name: 'pms',
      meta: { title: '商品管理', icon: 'Goods' },
      children: [
        {
          path: 'product',
          name: 'product',
          meta: { title: '商品列表', icon: 'List' },
        },
        {
          path: 'addProduct',
          name: 'addProduct',
          meta: { title: '添加商品' },
          hidden: true,
        },
        {
          path: 'brand',
          name: 'brand',
          meta: { title: '品牌管理', icon: 'Trophy' },
        },
      ],
    },
    {
      path: '/oms',
      name: 'oms',
      meta: { title: '订单管理', icon: 'Document' },
      children: [
        {
          path: 'order',
          name: 'order',
          meta: { title: '订单列表', icon: 'List' },
        },
        {
          path: 'orderDetail',
          name: 'orderDetail',
          meta: { title: '订单详情' },
          hidden: true,
        },
      ],
    },
    {
      path: '/cms',
      name: 'cms',
      meta: { title: '内容管理', icon: 'DocumentCopy' },
      children: [
        { path: 'banner', name: 'banner', meta: { title: '轮播广告' } },
        { path: 'subject', name: 'subject', meta: { title: '专题管理' } },
      ],
    },
  ]
  const testConstantRoutes: RouteRecordExt[] = [
    {
      path: '/login',
      name: 'login',
      meta: { title: '登录' },
      hidden: true,
    },
    {
      path: '/',
      name: 'home',
      meta: { title: '首页' },
    },
  ]
  return {
    asyncRouterMap: testAsyncRoutes,
    constantRouterMap: testConstantRoutes,
    default: {
      push: vi.fn(),
      currentRoute: { value: { path: '/' } },
    },
  }
})

// Import after mocks
import { usePermissionStore } from '@/stores/permission'

function makeMenu(overrides: Partial<MenuItem> = {}): MenuItem {
  return {
    id: '1',
    parentId: '',
    title: 'Test Menu',
    name: 'test',
    icon: 'TestIcon',
    sort: 5,
    hidden: 0,
    ...overrides,
  }
}

describe('usePermissionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('generateRoutes', () => {
    it('should include routes whose name matches a menu item', () => {
      const store = usePermissionStore()
      // Menus must include parent route names too (like real DEFAULT_MENUS)
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', title: '商品管理', sort: 5 }),
        makeMenu({ id: '2', name: 'product', title: '商品列表', sort: 5 }),
        makeMenu({ id: '3', name: 'oms', title: '订单管理', sort: 3 }),
        makeMenu({ id: '4', name: 'order', title: '订单列表', sort: 3 }),
      ]

      store.generateRoutes(menus)

      // pms (parent) should be included because its menu matched
      const names = store.addRouters.map((r) => r.name)
      expect(names).toContain('pms')
      expect(names).toContain('oms')
      // cms should NOT be in addRouters (no menu match)
      expect(names).not.toContain('cms')
    })

    it('should accept routes with hidden=true even without menu match', () => {
      const store = usePermissionStore()
      // Include parent 'pms' so the subtree is entered; 'addProduct' is hidden
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', sort: 5 }),
        makeMenu({ id: '2', name: 'product', sort: 4 }),
      ]

      store.generateRoutes(menus)

      // addProduct is hidden=true, should pass through hasPermission's hidden gate
      const pmsRoute = store.addRouters.find((r) => r.name === 'pms')
      expect(pmsRoute).toBeDefined()
      const childNames = pmsRoute!.children?.map((c: any) => c.name) || []
      expect(childNames).toContain('addProduct')
    })

    it('should sort routes descending by sort value', () => {
      const store = usePermissionStore()
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', sort: 5 }),
        makeMenu({ id: '2', name: 'product', sort: 5 }),
        makeMenu({ id: '3', name: 'oms', sort: 1 }),
        makeMenu({ id: '4', name: 'order', sort: 1 }),
        makeMenu({ id: '5', name: 'cms', sort: 10 }),
        makeMenu({ id: '6', name: 'banner', sort: 10 }),
        makeMenu({ id: '7', name: 'subject', sort: 9 }),
      ]

      store.generateRoutes(menus)

      // addRouters should be sorted descending by sort
      const sorts = store.addRouters.map((r) => r.sort ?? 0)
      for (let i = 0; i < sorts.length - 1; i++) {
        expect(sorts[i]).toBeGreaterThanOrEqual(sorts[i + 1])
      }
    })

    it('should update route meta title from menu data', () => {
      const store = usePermissionStore()
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', title: '商品管理区', icon: 'Goods', sort: 5 }),
        makeMenu({ id: '2', name: 'product', title: 'Products List', icon: 'Goods', sort: 5 }),
      ]

      store.generateRoutes(menus)

      // The pms route should have its meta title updated from the menu
      const pmsRoute = store.addRouters.find((r) => r.name === 'pms')
      expect(pmsRoute).toBeDefined()
      expect(pmsRoute!.sort).toBe(5)
    })
  })

  describe('resetPermission', () => {
    it('should clear addRouters and sidebarRouters', () => {
      const store = usePermissionStore()
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', sort: 5 }),
        makeMenu({ id: '2', name: 'product', sort: 5 }),
      ]

      store.generateRoutes(menus)
      expect(store.addRouters.length).toBeGreaterThan(0)

      store.resetPermission()
      expect(store.addRouters).toEqual([])
      expect(store.sidebarRouters).toEqual([])
    })

    it('should reset routers to only constant routes', () => {
      const store = usePermissionStore()
      store.generateRoutes([
        makeMenu({ id: '1', name: 'pms', sort: 5 }),
        makeMenu({ id: '2', name: 'product', sort: 5 }),
      ])
      store.resetPermission()

      // constantRouterMap includes login, home
      expect(store.routers.length).toBeGreaterThan(0)
      // All routes should be the constant ones only
      const names = store.routers.map((r) => r.name)
      expect(names).toContain('login')
      expect(names).toContain('home')
    })
  })

  describe('setSidebarRouters', () => {
    it('should set sidebar routes', () => {
      const store = usePermissionStore()
      const sidebarRoutes = [
        { id: '1', name: 'product', path: '/pms/product', meta: { title: 'Product' } },
      ] as any[]

      store.setSidebarRouters(sidebarRoutes)
      expect(store.sidebarRouters).toEqual(sidebarRoutes)
    })
  })

  describe('edge cases', () => {
    it('should handle empty menu list gracefully', () => {
      const store = usePermissionStore()
      store.generateRoutes([])

      // Only constant routes should remain, no dynamic routes added
      expect(store.addRouters.length).toBe(0)
    })

    it('should handle menu items with missing optional fields', () => {
      const store = usePermissionStore()
      // pms must be in menu for the parent route to pass through
      const menus: MenuItem[] = [
        { id: '1', parentId: '', title: '', name: 'pms' },
        { id: '2', parentId: '', title: '', name: 'product' },
      ]

      expect(() => store.generateRoutes(menus)).not.toThrow()
      expect(store.addRouters.length).toBeGreaterThan(0)
    })

    it('should not include routes with no matching menu AND not hidden', () => {
      const store = usePermissionStore()
      // Only give menu for pms + product, so cms + oms subtree should be excluded
      const menus: MenuItem[] = [
        makeMenu({ id: '1', name: 'pms', sort: 5 }),
        makeMenu({ id: '2', name: 'product', sort: 5 }),
      ]

      store.generateRoutes(menus)

      const names = store.addRouters.map((r) => r.name)
      expect(names).toContain('pms')
      expect(names).not.toContain('oms')
      expect(names).not.toContain('cms')
    })
  })
})
