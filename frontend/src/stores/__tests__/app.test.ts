/**
 * App Store 测试
 * 覆盖: 侧边栏展开/收起/切换、设备类型、fixedHeader 状态
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppStore } from '@/stores/app'

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should have sidebar opened by default', () => {
      const store = useAppStore()
      expect(store.sidebar.opened).toBe(true)
      expect(store.sidebar.withoutAnimation).toBe(false)
      expect(store.sidebarOpened).toBe(true)
    })

    it('should default to desktop device', () => {
      const store = useAppStore()
      expect(store.device).toBe('desktop')
    })

    it('should have fixedHeader enabled by default', () => {
      const store = useAppStore()
      expect(store.fixedHeader).toBe(true)
    })
  })

  describe('toggleSidebar', () => {
    it('should flip opened state', () => {
      const store = useAppStore()
      expect(store.sidebarOpened).toBe(true)

      store.toggleSidebar()
      expect(store.sidebarOpened).toBe(false)

      store.toggleSidebar()
      expect(store.sidebarOpened).toBe(true)
    })

    it('should set withoutAnimation to false', () => {
      const store = useAppStore()
      store.closeSidebar(true)
      expect(store.sidebar.withoutAnimation).toBe(true)

      store.toggleSidebar()
      expect(store.sidebar.opened).toBe(true)
      expect(store.sidebar.withoutAnimation).toBe(false)
    })
  })

  describe('closeSidebar', () => {
    it('should close sidebar with animation by default', () => {
      const store = useAppStore()
      store.closeSidebar()
      expect(store.sidebar.opened).toBe(false)
      expect(store.sidebar.withoutAnimation).toBe(false)
    })

    it('should close sidebar without animation when flag set', () => {
      const store = useAppStore()
      store.closeSidebar(true)
      expect(store.sidebar.opened).toBe(false)
      expect(store.sidebar.withoutAnimation).toBe(true)
    })
  })

  describe('openSidebar', () => {
    it('should open sidebar and reset animation flag', () => {
      const store = useAppStore()
      store.closeSidebar(true)
      expect(store.sidebar.opened).toBe(false)

      store.openSidebar()
      expect(store.sidebar.opened).toBe(true)
      expect(store.sidebar.withoutAnimation).toBe(false)
    })

    it('should be idempotent (opening when already open)', () => {
      const store = useAppStore()
      expect(store.sidebar.opened).toBe(true)

      store.openSidebar()
      expect(store.sidebar.opened).toBe(true)
    })
  })

  describe('toggleDevice', () => {
    it('should switch device to mobile', () => {
      const store = useAppStore()
      store.toggleDevice('mobile')
      expect(store.device).toBe('mobile')
    })

    it('should switch back to desktop', () => {
      const store = useAppStore()
      store.toggleDevice('mobile')
      store.toggleDevice('desktop')
      expect(store.device).toBe('desktop')
    })
  })

  describe('edge cases', () => {
    it('should handle rapid sidebar toggles', () => {
      const store = useAppStore()
      store.toggleSidebar()
      store.toggleSidebar()
      store.toggleSidebar()
      expect(store.sidebar.opened).toBe(false)
    })

    it('should maintain independent state between stores', () => {
      const store1 = useAppStore()
      const store2 = useAppStore()
      expect(store1).toBe(store2) // same Pinia instance

      store1.toggleSidebar()
      expect(store2.sidebar.opened).toBe(false)
    })
  })
})
