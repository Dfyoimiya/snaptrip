<script setup lang="ts">
/**
 * ============================================
 * 页签栏组件 (TabBar)
 *
 * 浏览器风格的多页签栏，置于搜索栏下方:
 *   - 页签横向排列，可滚动
 *   - 点击切换活跃页签
 *   - 关闭按钮 (固定页签在唯一时隐藏)
 *   - 拖拽排序
 *   - 右键菜单: 关闭 / 关闭其他 / 关闭右侧 / 关闭全部
 *   - "+" 新建页签按钮
 * ============================================
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTabStore, type Tab } from '@/stores/tabs'

const router = useRouter()
const route = useRoute()
const tabStore = useTabStore()

// ── 拖拽状态 ──
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

// ── 右键菜单 ──
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

onMounted(() => window.addEventListener('click', closeContextMenu))
onUnmounted(() => window.removeEventListener('click', closeContextMenu))

// ── 页签操作 ──
function handleTabClick(tab: Tab) {
  tabStore.setActiveTab(tab.id)
  router.push({ path: tab.path, query: tab.query || {} })
}

function handleTabClose(tab: Tab, e: MouseEvent) {
  e.stopPropagation()
  tabStore.closeTab(tab.id)
}

function handleNewTab() {
  tabStore.openTab('/', '首页', undefined, true)
  router.push('/')
}

// ── 计算可关闭性 ──
const pinnedCount = computed(() => tabStore.tabs.filter(t => t.pinned).length)

function isClosable(tab: Tab): boolean {
  if (!tab.pinned) return true
  // 固定页签: 只有当它是唯一固定页签时不可关闭
  return pinnedCount.value > 1
}

// ── 路由变化时同步活跃页签 ──
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
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center gap-1 overflow-x-auto tab-scroll">
        <!-- 页签列表 -->
        <button
          v-for="(tab, idx) in tabStore.tabs"
          :key="tab.id"
          class="tab-item"
          :class="{
            active: tab.id === tabStore.activeTabId,
            'drag-over': dragOverIndex === idx && dragIndex !== idx,
            dragging: dragIndex === idx,
          }"
          draggable="true"
          @dragstart="onDragStart(idx, $event)"
          @dragover="onDragOver(idx, $event)"
          @dragleave="onDragLeave"
          @drop="onDrop(idx)"
          @dragend="onDragEnd"
          @click="handleTabClick(tab)"
          @contextmenu="onContextMenu(tab.id, $event)"
        >
          <span class="tab-title">{{ tab.title }}</span>
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
  background: transparent;
}

.tab-scroll {
  height: 46px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.tab-scroll::-webkit-scrollbar {
  display: none;
}

/* ── 页签项 ── */
.tab-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  height: 42px;
  padding: 0 14px;
  border-radius: 9px;
  font-size: 13px;
  color: #999;
  background: transparent;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  user-select: none;
  flex-shrink: 0;
  max-width: 1080px;
  min-width: 50px;
}

.tab-item:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #666;
}

.tab-item.active {
  background: #ffffff;
  color: #ff5000;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.04);
}

.tab-item.dragging {
  opacity: 0.5;
}

.tab-item.drag-over {
  box-shadow: inset 0 0 0 2px #ff5000;
}

/* ── 页签标题 ── */
.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
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
  margin-left: auto;
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
  margin-left: 2px;
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
  background: #fff;
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
  color: #333;
  border-radius: 4px;
  transition: background 0.1s;
}

.tab-context-menu button:hover {
  background: #f5f5f5;
}

.tab-context-menu hr {
  margin: 4px 8px;
  border: none;
  border-top: 1px solid #eee;
}
</style>
