import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { HOME_TAB_PATH, useTabStore } from '@/stores/tab'
import type { TabView } from '@/stores/tab'

function createTab(path: string, keepAlive = false): TabView {
  return {
    name: path.slice(1) || 'root',
    path,
    fullPath: path,
    meta: { keepAlive },
    title: path === HOME_TAB_PATH ? '首页' : '测试页面',
  }
}

describe('useTabStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('keeps home when it is the last tab', () => {
    const store = useTabStore()
    store.addView(createTab(HOME_TAB_PATH, true))

    store.removeView(HOME_TAB_PATH)

    expect(store.tabList.map((tab) => tab.path)).toEqual([HOME_TAB_PATH])
  })

  it('keeps home when closing all tabs', () => {
    const store = useTabStore()
    store.addView(createTab(HOME_TAB_PATH, true))
    store.addView(createTab('/pms/product', true))

    store.closeAllViews()

    expect(store.tabList.map((tab) => tab.path)).toEqual([HOME_TAB_PATH])
    expect(store.cachedViews).toEqual(['home'])
  })
})
