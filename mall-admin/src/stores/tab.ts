import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RouteLocationNormalized } from 'vue-router'

/** Tab 状态管理（多标签页） */
export const useTabStore = defineStore('tab', () => {
  // State
  const visitedViews = ref<TabView[]>([])
  const cachedViews = ref<string[]>([])

  // Getters
  const tabList = computed(() => visitedViews.value)

  // Actions
  /** 添加标签页 */
  function addView(view: TabView) {
    if (view.meta?.noTab) return
    // 已存在则不重复添加
    if (visitedViews.value.some((v) => v.path === view.path)) return
    visitedViews.value.push(view)
    // 缓存
    if (view.meta?.keepAlive && view.name) {
      if (!cachedViews.value.includes(view.name as string)) {
        cachedViews.value.push(view.name as string)
      }
    }
  }

  /** 关闭标签页 */
  function removeView(path: string) {
    const index = visitedViews.value.findIndex((v) => v.path === path)
    if (index > -1) {
      const view = visitedViews.value[index]
      visitedViews.value.splice(index, 1)
      // 移除缓存
      if (view.name) {
        const i = cachedViews.value.indexOf(view.name as string)
        if (i > -1) cachedViews.value.splice(i, 1)
      }
    }
  }

  /** 关闭其他标签页 */
  function closeOthersViews(path: string) {
    visitedViews.value = visitedViews.value.filter(
      (v) => v.meta?.affix || v.path === path
    )
    cachedViews.value = visitedViews.value
      .filter((v) => v.meta?.keepAlive && v.name)
      .map((v) => v.name as string)
  }

  /** 关闭所有标签页（保留固定的） */
  function closeAllViews() {
    visitedViews.value = visitedViews.value.filter((v) => v.meta?.affix)
    cachedViews.value = []
  }

  return {
    visitedViews,
    cachedViews,
    tabList,
    addView,
    removeView,
    closeOthersViews,
    closeAllViews,
  }
})

/** Tab 视图项 */
export interface TabView {
  name?: string | symbol
  path: string
  fullPath: string
  meta?: Record<string, any>
  title?: string
}
