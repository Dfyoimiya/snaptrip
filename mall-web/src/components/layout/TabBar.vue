<script setup lang="ts">
/**
 * ============================================
 * 页签栏组件 (TabBar)
 *
 * 浏览器风格的多页签栏，置于搜索栏下方:
 *   - 页签横向排列，带溢出滚动箭头
 *   - 点击切换活跃页签
 *   - 页签图标 (来自 tab.icon)
 *   - 关闭按钮 (首页永远不可关闭)
 *   - 拖拽排序
 *   - 右键菜单: 关闭 / 关闭其他 / 关闭右侧 / 关闭全部
 *   - "+" 新建页签按钮
 *   - 激活页签自动滚动到可见区域
 *   - localStorage 持久化 (由 tabStore 管理)
 * ============================================
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTabStore, type Tab } from '@/stores/tabs'

const router = useRouter()
const route = useRoute()
const tabStore = useTabStore()

// ═══════════════════════════════════════════
// 溢出滚动
// ═══════════════════════════════════════════
const tabsContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

function updateScrollState() {
  const el = tabsContainer.value
  if (!el) return
  canScrollLeft.value = el.scrollLeft > 1
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 1
}

function scrollLeft() {
  tabsContainer.value?.scrollBy({ left: -200, behavior: 'smooth' })
}

function scrollRight() {
  tabsContainer.value?.scrollBy({ left: 200, behavior: 'smooth' })
}

function scrollWheel(e: WheelEvent) {
  tabsContainer.value?.scrollBy({ left: e.deltaY, behavior: 'auto' })
}

// 激活页签变化时自动滚动到可见区域
watch(() => tabStore.activeTabId, () => {
  nextTick(() => {
    const el = tabsContainer.value
    if (!el) return
    const activeEl = el.querySelector('.tab-item.active') as HTMLElement | null
    if (activeEl) {
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
    }
  })
})

onMounted(() => {
  updateScrollState()
  tabsContainer.value?.addEventListener('scroll', updateScrollState, { passive: true })
  window.addEventListener('resize', updateScrollState)
})

onUnmounted(() => {
  tabsContainer.value?.removeEventListener('scroll', updateScrollState)
  window.removeEventListener('resize', updateScrollState)
})

// ═══════════════════════════════════════════
// 拖拽排序
// ═══════════════════════════════════════════
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
const draggedTab = ref<Tab | null>(null)

function onDragStart(idx: number, e: DragEvent) {
  dragIndex.value = idx
  draggedTab.value = tabStore.tabs[idx]
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', tabStore.tabs[idx].id)
  }
}

function onDragOver(idx: number, e: DragEvent) {
  e.preventDefault()
  dragOverIndex.value = idx
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

function onDragLeave() {
  dragOverIndex.value = null
}

function onDrop(idx: number) {
  if (dragIndex.value !== null && dragIndex.value !== idx) {
    tabStore.reorderTabs(dragIndex.value, idx)
  }
  dragIndex.value = null
  dragOverIndex.value = null
  draggedTab.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
  draggedTab.value = null
}

// ═══════════════════════════════════════════
// 右键菜单
// ═══════════════════════════════════════════
const contextMenu = ref<{ show: boolean; x: number; y: number; tabId: string }>({
  show: false,
  x: 0,
  y: 0,
  tabId: '',
})

function onContextMenu(tabId: string, e: MouseEvent) {
  e.preventDefault()
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, tabId }
}

function closeContextMenu() {
  contextMenu.value.show = false
}

function handleContextAction(action: string) {
  const id = contextMenu.value.tabId
  switch (action) {
    case 'close':
      tabStore.closeTab(id)
      break
    case 'closeOthers':
      tabStore.closeOthers(id)
      break
    case 'closeRight':
      tabStore.closeRight(id)
      break
    case 'closeAll':
      tabStore.closeAll()
      break
  }
  closeContextMenu()
}

onMounted(() => {
  window.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  window.removeEventListener('click', closeContextMenu)
})

// ═══════════════════════════════════════════
// 页签操作
// ═══════════════════════════════════════════
function handleTabClick(tab: Tab) {
  tabStore.setActiveTab(tab.id)
  router.push({ path: tab.path, query: tab.query || {} })
}

function handleTabClose(tab: Tab, e: MouseEvent) {
  e.stopPropagation()
  if (tab.id === 'home') return // 首页永远不可关闭
  tabStore.closeTab(tab.id)
}

function handleNewTab() {
  tabStore.openTab('/', '首页', undefined, true)
  router.push('/')
}

/** 首页永远不可关闭；其余固定页签仅当固定页签 > 1 时可关闭 */
function isClosable(tab: Tab): boolean {
  if (tab.id === 'home') return false
  if (!tab.pinned) return true
  return tabStore.tabs.filter(t => t.pinned).length > 1
}

// ═══════════════════════════════════════════
// 路由变化时同步活跃页签
// ═══════════════════════════════════════════
watch(
  () => route.path,
  (newPath) => {
    const matchingTab = tabStore.tabs.find(t => t.path === newPath)
    if (matchingTab) {
      tabStore.setActiveTab(matchingTab.id)
    }
  },
)
</script>

<template>
  <div class="tab-bar-wrapper">
    <div class="flex items-center h-[34px] gap-0">
      <!-- 左滚动箭头 -->
      <button
        v-if="canScrollLeft"
        class="tab-scroll-btn"
        aria-label="向左滚动"
        @click="scrollLeft"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <!-- 页签滚动容器 -->
      <div
        ref="tabsContainer"
        class="overflow-hidden flex-1"
        @wheel.prevent="scrollWheel"
      >
        <div class="flex items-center gap-1 px-1 h-full">
          <button
            v-for="(tab, idx) in tabStore.tabs"
            :key="tab.id"
            class="tab-item"
            :class="{
              active: tab.id === tabStore.activeTabId,
              'drag-over': dragOverIndex === idx && dragIndex !== idx,
              dragging: dragIndex === idx,
            }"
            :title="tab.title"
            draggable="true"
            @dragstart="onDragStart(idx, $event)"
            @dragover="onDragOver(idx, $event)"
            @dragleave="onDragLeave"
            @drop="onDrop(idx)"
            @dragend="onDragEnd"
            @click="handleTabClick(tab)"
            @contextmenu="onContextMenu(tab.id, $event)"
          >
            <!-- 页签图标 -->
            <span v-if="tab.icon" class="tab-icon">{{ tab.icon }}</span>
            <!-- 页签标题 -->
            <span class="tab-title">{{ tab.title }}</span>
            <!-- 关闭按钮 (首页不可关闭不显示) -->
            <span
              v-if="isClosable(tab)"
              class="tab-close"
              @click="handleTabClose(tab, $event)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </span>
          </button>

          <!-- 新建页签 -->
          <button
            v-if="tabStore.canAddMore"
            class="tab-new-btn"
            title="新建页签"
            @click="handleNewTab"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 右滚动箭头 -->
      <button
        v-if="canScrollRight"
        class="tab-scroll-btn"
        aria-label="向右滚动"
        @click="scrollRight"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div
        v-if="contextMenu.show"
        class="tab-context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <button @click="handleContextAction('close')">关闭页签</button>
        <button @click="handleContextAction('closeOthers')">关闭其他页签</button>
        <button @click="handleContextAction('closeRight')">关闭右侧页签</button>
        <hr />
        <button @click="handleContextAction('closeAll')">关闭全部页签</button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tab-bar-wrapper {
  position: fixed;
  top: 64px;
  left: 208px;
  right: 19px;
  z-index: 49;
  padding: 2px 8px;
  background: var(--mall-glass-bg-light);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--mall-glass-border);
  border-radius: 10px;
  box-shadow: var(--mall-glass-shadow-soft);
}

/* ── 滚动箭头按钮 ── */
.tab-scroll-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: #999;
  flex-shrink: 0;
  transition: all 0.15s;
}

.tab-scroll-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #333;
}

/* ── 页签项 ── */
.tab-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  height: 28px;
  min-width: 100px;
  max-width: 200px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #999;
  background: transparent;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  position: relative;
  user-select: none;
  flex-shrink: 0;
  border-bottom: 2px solid transparent;
}

.tab-item:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #666;
}

.tab-item.active {
  color: #ff5000;
  font-weight: 600;
  background: rgba(255, 80, 0, 0.08);
  border-bottom-color: #ff5000;
}

.tab-item.dragging {
  opacity: 0.5;
}

.tab-item.drag-over {
  box-shadow: inset 0 0 0 2px #ff5000;
}

/* ── 页签图标 ── */
.tab-icon {
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
}

/* ── 页签标题 ── */
.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 关闭按钮 ── */
.tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-left: 2px;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}

.tab-item:hover .tab-close,
.tab-item.active .tab-close {
  opacity: 0.5;
}

.tab-close:hover {
  opacity: 1 !important;
  background: rgba(0, 0, 0, 0.08);
}

/* ── 新建按钮 ── */
.tab-new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  color: #bbb;
  flex-shrink: 0;
  transition: all 0.15s;
}

.tab-new-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #666;
}

/* ── 右键菜单 ── */
.tab-context-menu {
  position: fixed;
  z-index: 9999;
  color: var(--mall-text);
  background: var(--mall-surface);
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  padding: 4px;
  min-width: 140px;
}

.tab-context-menu button {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--mall-text);
  border-radius: 4px;
  transition: background 0.1s;
}

.tab-context-menu button:hover {
  background: var(--mall-hover);
}

.tab-context-menu hr {
  margin: 4px 8px;
  border: none;
  border-top: 1px solid var(--mall-border);
}
</style>
