/**
 * ============================================
 * 全局布局状态管理 (Pinia Store)
 *
 * 管理：
 *   - 左侧导航栏：hover 展开 / 点击锁定（桌面端三栏布局）
 *   - 商品对比列表
 *   - 屏幕尺寸检测
 *
 * 持久化到 localStorage:
 *   - 浏览器足迹历史
 *   - 对比产品列表
 * ============================================
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ProductSummary } from '@/types'

const HISTORY_KEY = 'snaptrip_browse_history'
const COMPARE_KEY = 'snaptrip_compare_products'
const THEME_KEY = 'snaptrip_theme'
const MAX_HISTORY = 50
const MAX_COMPARE = 5

export type ThemeType = 'light' | 'dark'

function loadHistory(): ProductSummary[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

function loadCompare(): ProductSummary[] {
  try {
    const raw = localStorage.getItem(COMPARE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

function persistHistory(items: ProductSummary[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, MAX_HISTORY)))
  } catch { /* ignore */ }
}

function persistCompare(items: ProductSummary[]) {
  try {
    localStorage.setItem(COMPARE_KEY, JSON.stringify(items))
  } catch { /* ignore */ }
}

export const useLayoutStore = defineStore('layout', () => {
  // ── State ──

  // 左侧边栏 — 始终展开
  const leftSidebarExpanded = ref(true)
  const leftSidebarLocked = ref(true)
  const theme = ref<ThemeType>(
    localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light',
  )

  // 对比 & 历史
  const compareProducts = ref<ProductSummary[]>(loadCompare())
  const browseHistory = ref<ProductSummary[]>(loadHistory())
  const isComparing = ref(false)

  // 屏幕尺寸跟踪
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => {
      windowWidth.value = window.innerWidth
    })
  }

  // ── Getters ──

  /** 左侧边栏实际宽度：折叠 64px，展开 200px */
  const leftSidebarWidth = computed<string>(() =>
    leftSidebarExpanded.value || leftSidebarLocked.value ? '200px' : '64px',
  )

  /** 是否为大屏幕（>= 1024px） */
  const isLargeScreen = computed<boolean>(() => windowWidth.value >= 1024)

  /** 是否处于对比视图模式 */
  const compareActive = computed<boolean>(() => isComparing.value)

  // ── Actions: 左侧边栏 ──

  /** 切换左侧边栏展开/折叠 */
  function toggleLeftSidebar() {
    leftSidebarExpanded.value = !leftSidebarExpanded.value
  }

  /** 锁定左侧边栏（固定展开） */
  function lockLeftSidebar() {
    leftSidebarLocked.value = true
    leftSidebarExpanded.value = true
  }

  /** 解锁左侧边栏（恢复 hover 展开） */
  function unlockLeftSidebar() {
    leftSidebarLocked.value = false
    leftSidebarExpanded.value = false
  }

  /** 将当前主题同步到根节点 */
  function applyTheme() {
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
    document.documentElement.style.colorScheme = theme.value
  }

  /** 切换并持久化亮色/暗色主题 */
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem(THEME_KEY, theme.value)
    applyTheme()
  }

  // ── Actions: 浏览足迹 ──

  /** 添加商品到浏览足迹 */
  function addToHistory(product: ProductSummary) {
    const existing = browseHistory.value.findIndex(p => p.id === product.id)
    if (existing >= 0) {
      browseHistory.value.splice(existing, 1)
    }
    browseHistory.value.unshift(product)
    if (browseHistory.value.length > MAX_HISTORY) {
      browseHistory.value = browseHistory.value.slice(0, MAX_HISTORY)
    }
    persistHistory(browseHistory.value)
  }

  /** 清空浏览足迹 */
  function clearHistory() {
    browseHistory.value = []
    persistHistory([])
  }

  // ── Actions: 商品对比 ──

  /** 添加商品到对比列表 */
  function addToCompare(product: ProductSummary) {
    if (compareProducts.value.length >= MAX_COMPARE) return
    if (compareProducts.value.some(p => p.id === product.id)) return
    compareProducts.value.push(product)
    persistCompare(compareProducts.value)
  }

  /** 从对比列表中移除商品 */
  function removeFromCompare(productId: string | number) {
    compareProducts.value = compareProducts.value.filter(p => p.id !== productId)
    persistCompare(compareProducts.value)
    if (compareProducts.value.length < 2) {
      isComparing.value = false
    }
  }

  /** 清空对比列表 */
  function clearCompare() {
    compareProducts.value = []
    isComparing.value = false
    persistCompare([])
  }

  /** 开始对比 (打开对比视图) */
  function startCompare() {
    if (compareProducts.value.length >= 2) {
      isComparing.value = true
    }
  }

  /** 结束对比 (关闭对比视图) */
  function endCompare() {
    isComparing.value = false
  }

  return {
    // state
    leftSidebarExpanded,
    leftSidebarLocked,
    theme,
    compareProducts,
    browseHistory,
    isComparing,
    // getters
    leftSidebarWidth,
    isLargeScreen,
    compareActive,
    // actions: left sidebar
    toggleLeftSidebar,
    lockLeftSidebar,
    unlockLeftSidebar,
    applyTheme,
    toggleTheme,
    // actions: history
    addToHistory,
    clearHistory,
    // actions: compare
    addToCompare,
    removeFromCompare,
    clearCompare,
    startCompare,
    endCompare,
  }
})
