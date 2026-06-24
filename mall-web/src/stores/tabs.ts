/**
 * ============================================
 * 页签状态管理 (Pinia Store)
 *
 * 浏览器风格的多页签系统:
 *   - 默认 "首页" 页签 (固定，不可关闭)
 *   - 用户点击导航时自动打开/切换页签
 *   - 支持拖拽排序、关闭、右键菜单
 *   - 持久化到 localStorage
 * ============================================
 */

import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

export interface Tab {
  id: string
  title: string
  path: string
  query?: Record<string, string>
  pinned: boolean
  /** 页签图标 (emoji 或 icon name) */
  icon?: string
}

/** 从 path 推断默认标题 */
function defaultTitle(path: string): string {
  const map: Record<string, string> = {
    '/': '首页',
    '/search': '搜索',
    '/category': '全部商品',
    '/new': '新品上架',
    '/hot': '人气推荐',
    '/coupons': '优惠券',
    '/shopping-guide': '帮我挑',
    '/cart': '购物车',
    '/member': '会员中心',
    '/member/orders': '我的订单',
    '/member/favorites': '我的收藏',
    '/member/address': '收货地址',
    '/member/coupons': '我的优惠券',
    '/member/history': '浏览足迹',
    '/member/settings': '账号设置',
  }
  if (map[path]) return map[path]
  if (path.startsWith('/product/')) return '商品详情'
  if (path.startsWith('/order/')) return '订单详情'
  if (path.startsWith('/notice/')) return '公告详情'
  return '新页签'
}

function defaultIcon(path: string): string {
  const map: Record<string, string> = {
    '/': '🏠',
    '/search': '🔍',
    '/category': '📂',
    '/new': '✨',
    '/hot': '🔥',
    '/coupons': '🎫',
    '/shopping-guide': '🤖',
    '/cart': '🛒',
    '/member': '👤',
    '/member/orders': '📦',
    '/member/favorites': '❤️',
    '/member/history': '🕐',
    '/member/settings': '⚙️',
  }
  return map[path] || '📄'
}

const STORAGE_KEY = '_snaptrip_tabs'
const MAX_TABS = 15

function loadTabs(): Tab[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

function saveTabs(tabs: Tab[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tabs))
  } catch { /* ignore */ }
}

export const useTabStore = defineStore('tabs', () => {
  // ── State ──
  const savedTabs = loadTabs()
  const tabs = ref<Tab[]>(
    savedTabs.length > 0
      ? savedTabs
      : [{ id: 'home', title: '首页', path: '/', pinned: true, icon: '🏠' }],
  )
  const activeTabId = ref<string>(tabs.value[0]?.id || 'home')

  // ── Getters ──
  const activeTab = computed(() => tabs.value.find(t => t.id === activeTabId.value))
  const tabCount = computed(() => tabs.value.length)
  const canAddMore = computed(() => tabs.value.length < MAX_TABS)

  // ── Actions ──
  function _persist() {
    // 只持久化非临时的页签 (排除产品详情等，保留核心导航)
    const toSave = tabs.value.filter(t => t.pinned || !t.path.startsWith('/product/'))
    saveTabs(toSave)
  }

  /** 打开或切换到页签，forceNew 为 true 时始终创建新页签 */
  function openTab(path: string, title?: string, query?: Record<string, string>, forceNew = false) {
    // 检查是否已存在相同 path 的页签 (非强制新建时复用)
    if (!forceNew) {
      const existing = tabs.value.find(t => t.path === path)
      if (existing) {
        activeTabId.value = existing.id
        if (query) existing.query = query
        return existing.id
      }
    }

    // 达到上限时，关闭最后一个非固定页签
    if (!canAddMore.value) {
      const lastUnpinned = [...tabs.value].reverse().find(t => !t.pinned)
      if (lastUnpinned) closeTab(lastUnpinned.id)
    }

    const id = `tab-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    const newTab: Tab = {
      id,
      title: title || defaultTitle(path),
      path,
      query,
      pinned: false,
      icon: defaultIcon(path),
    }
    tabs.value.push(newTab)
    activeTabId.value = id
    _persist()
    return id
  }

  /** 关闭页签 */
  function closeTab(id: string) {
    const tab = tabs.value.find(t => t.id === id)
    if (!tab) return
    if (tab.pinned && tabs.value.filter(t => t.pinned).length <= 1) return // 至少保留一个固定页签

    const idx = tabs.value.findIndex(t => t.id === id)
    tabs.value.splice(idx, 1)

    // 如果关闭的是当前活跃页签，切换到相邻页签
    if (activeTabId.value === id) {
      const newIdx = Math.min(idx, tabs.value.length - 1)
      activeTabId.value = tabs.value[newIdx]?.id || 'home'
    }
    _persist()
  }

  /** 关闭其他页签 */
  function closeOthers(id: string) {
    tabs.value = tabs.value.filter(t => t.id === id || t.pinned)
    activeTabId.value = id
    _persist()
  }

  /** 关闭所有非固定页签 */
  function closeAll() {
    tabs.value = tabs.value.filter(t => t.pinned)
    activeTabId.value = tabs.value[0]?.id || 'home'
    _persist()
  }

  /** 关闭右侧页签 */
  function closeRight(id: string) {
    const idx = tabs.value.findIndex(t => t.id === id)
    if (idx === -1) return
    const pinned = tabs.value.filter(t => t.pinned)
    tabs.value = [...tabs.value.slice(0, idx + 1), ...pinned.filter(p => tabs.value.indexOf(p) > idx)]
    // remove duplicate pinned
    const seen = new Set<string>()
    tabs.value = tabs.value.filter(t => {
      if (seen.has(t.id)) return false
      seen.add(t.id)
      return true
    })
    activeTabId.value = id
    _persist()
  }

  /** 切换活跃页签 */
  function setActiveTab(id: string) {
    if (tabs.value.find(t => t.id === id)) {
      activeTabId.value = id
    }
  }

  /** 更新页签标题 */
  function updateTabTitle(id: string, title: string) {
    const tab = tabs.value.find(t => t.id === id)
    if (tab) {
      tab.title = title
      _persist()
    }
  }

  /** 拖拽排序 */
  function reorderTabs(fromIndex: number, toIndex: number) {
    const item = tabs.value.splice(fromIndex, 1)[0]
    if (item) {
      tabs.value.splice(toIndex, 0, item)
      _persist()
    }
  }

  return {
    tabs,
    activeTabId,
    activeTab,
    tabCount,
    canAddMore,
    openTab,
    closeTab,
    closeOthers,
    closeAll,
    closeRight,
    setActiveTab,
    updateTabTitle,
    reorderTabs,
  }
})
