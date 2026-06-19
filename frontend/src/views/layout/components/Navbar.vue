<script lang="ts" setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Fold, Expand, Search, RefreshRight, FullScreen,
  Bell, Setting, Close, Moon, Sunny, Right,
} from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'
import { useTabStore } from '@/stores/tab'
import { HOME_TAB_PATH } from '@/stores/tab'
import type { TabView } from '@/stores/tab'
import type { RouteRecordExt } from '@/types'

interface SearchRouteItem {
  path: string
  title: string
  breadcrumb: string
  icon?: string
}

const appStore = useAppStore()
const permissionStore = usePermissionStore()
const tabStore = useTabStore()
const route = useRoute()
const router = useRouter()

const sidebar = computed(() => appStore.sidebar)
const tabs = computed(() => tabStore.tabList)
const activePath = computed(() => route.path)
const theme = computed(() => appStore.theme)
const searchVisible = ref(false)
const searchKeyword = ref('')
const searchInputRef = ref<HTMLInputElement>()

function resolveRoutePath(parentPath: string, routePath: string): string {
  if (routePath.startsWith('/')) return routePath
  if (!routePath) return parentPath || '/'
  return `${parentPath.replace(/\/$/, '')}/${routePath}`.replace(/\/+/g, '/')
}

function collectSearchRoutes(
  routes: RouteRecordExt[],
  parentPath = '',
  parents: string[] = [],
): SearchRouteItem[] {
  return routes.flatMap((item) => {
    if (item.hidden || item.meta?.hidden) return []
    const path = resolveRoutePath(parentPath, item.path)
    const title = item.meta?.title
    const titles = title ? [...parents, title] : parents
    const children = item.children ? collectSearchRoutes(item.children, path, titles) : []
    const self = title && (!item.children || item.children.length === 0)
      ? [{ path, title, breadcrumb: titles.join(' / '), icon: item.meta?.icon }]
      : []
    return [...self, ...children]
  })
}

const searchableRoutes = computed(() => {
  const seen = new Set<string>()
  return collectSearchRoutes(permissionStore.routers).filter((item) => {
    if (seen.has(item.path)) return false
    seen.add(item.path)
    return !['/login', '/403', '/404'].includes(item.path)
  })
})

const searchResults = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return searchableRoutes.value.slice(0, 8)
  return searchableRoutes.value
    .filter((item) =>
      `${item.title} ${item.breadcrumb} ${item.path}`.toLowerCase().includes(keyword),
    )
    .slice(0, 12)
})

// 面包屑
const breadcrumbs = computed(() => {
  return route.matched.filter(
    (item) => item.meta?.title && item.meta.title !== '首页',
  )
})

// 通知
const notifications = ref([
  { id: 1, title: '新订单提醒', content: '您有新的待处理订单', time: '5分钟前' },
  { id: 2, title: '库存预警', content: '商品 "iPhone 15" 库存不足', time: '1小时前' },
  { id: 3, title: '系统通知', content: '系统将于今晚进行维护', time: '2小时前' },
])
const unreadCount = ref(3)

// Tab右键菜单
const tabMenuVisible = ref(false)
const tabMenuPosition = ref({ x: 0, y: 0 })
const selectedTab = ref('')

function toggleSidebar() { appStore.toggleSidebar() }
function openSearch() { searchVisible.value = true }
function closeSearch() {
  searchVisible.value = false
  searchKeyword.value = ''
}
async function navigateToSearchResult(item: SearchRouteItem) {
  closeSearch()
  await router.push(item.path)
}
async function handleSearchEnter() {
  if (searchResults.value.length > 0) {
    await navigateToSearchResult(searchResults.value[0])
  }
}
function handleGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openSearch()
  } else if (event.key === 'Escape' && searchVisible.value) {
    closeSearch()
  }
}

// 刷新页面
function handleRefresh() {
  router.replace({ path: '/redirect' + route.fullPath })
}

// 全屏
function handleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

// Tab 操作
function onTabClick(tab: TabView) {
  router.push(tab.fullPath)
}
function isLastHomeTab(tab: TabView): boolean {
  return tabs.value.length === 1 && tab.path === HOME_TAB_PATH
}
function onTabRemove(path: string) {
  const isActive = path === route.path
  tabStore.removeView(path)
  if (tabs.value.length === 0) {
    router.push(HOME_TAB_PATH)
  } else if (isActive) {
    router.push(tabs.value[tabs.value.length - 1].fullPath)
  }
}

// Tab 右键菜单
function onTabContextmenu(e: MouseEvent, tab: TabView) {
  e.preventDefault()
  if (isLastHomeTab(tab)) {
    closeTabMenu()
    return
  }
  selectedTab.value = tab.path
  tabMenuPosition.value = { x: e.clientX, y: e.clientY }
  tabMenuVisible.value = true
}
function closeTabMenu() { tabMenuVisible.value = false }
function handleCloseOthers() {
  tabStore.closeOthersViews(selectedTab.value)
  router.push(selectedTab.value)
  closeTabMenu()
}
function handleCloseAll() {
  tabStore.closeAllViews()
  if (tabs.value.length > 0) {
    router.push(tabs.value[tabs.value.length - 1].fullPath)
  } else {
    router.push(HOME_TAB_PATH)
  }
  closeTabMenu()
}
function handleCloseRight() {
  const idx = tabs.value.findIndex(t => t.path === selectedTab.value)
  for (let i = tabs.value.length - 1; i > idx; i--) {
    tabStore.removeView(tabs.value[i].path)
  }
  closeTabMenu()
}

watch(searchVisible, async (visible) => {
  if (visible) {
    await nextTick()
    searchInputRef.value?.focus()
  }
})

onMounted(() => window.addEventListener('keydown', handleGlobalKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', handleGlobalKeydown))
</script>

<template>
  <div class="navbar-vben">
    <!-- 顶部工具栏 -->
    <div class="navbar-top">
      <!-- 左侧 -->
      <div class="top-left">
        <div class="hamburger" @click="toggleSidebar">
          <el-icon :size="18"><Fold v-if="sidebar.opened" /><Expand v-else /></el-icon>
        </div>
        <el-breadcrumb separator="/" class="breadcrumb">
          <el-breadcrumb-item :to="{ path: '/' }">
            <span>首页</span>
          </el-breadcrumb-item>
          <el-breadcrumb-item
            v-for="item in breadcrumbs"
            :key="item.path"
            :to="item.path"
          >
            <span>{{ item.meta?.title }}</span>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <!-- 右侧工具 -->
      <div class="top-right">
        <!-- 搜索 -->
        <div
          class="search-box"
          role="button"
          tabindex="0"
          @click="openSearch"
          @keydown.enter="openSearch"
        >
          <el-icon :size="15"><Search /></el-icon>
          <span class="search-text">搜索</span>
          <kbd class="search-kbd">Ctrl K</kbd>
        </div>

        <!-- 工具按钮 -->
        <div class="tool-btn" title="刷新" @click="handleRefresh">
          <el-icon :size="16"><RefreshRight /></el-icon>
        </div>
        <div class="tool-btn" title="全屏" @click="handleFullscreen">
          <el-icon :size="16"><FullScreen /></el-icon>
        </div>
        <div class="tool-btn" title="切换主题" @click="appStore.toggleTheme">
          <el-icon :size="16"><Moon v-if="theme === 'light'" /><Sunny v-else /></el-icon>
        </div>
        <div class="tool-btn" title="设置" @click="router.push('/setting/oss')">
          <el-icon :size="16"><Setting /></el-icon>
        </div>

        <!-- 通知 -->
        <el-dropdown trigger="click" :teleported="false">
          <div class="tool-btn notification-btn">
            <el-icon :size="16"><Bell /></el-icon>
            <span v-if="unreadCount > 0" class="notification-dot">{{ unreadCount }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="notification-dropdown-vben">
              <div class="notif-header">
                <span class="notif-title">消息通知</span>
                <el-tag size="small" type="primary">{{ unreadCount }} 未读</el-tag>
              </div>
              <el-dropdown-item v-for="n in notifications" :key="n.id">
                <div class="notif-item">
                  <div class="notif-item-title">{{ n.title }}</div>
                  <div class="notif-item-desc">{{ n.content }}</div>
                  <div class="notif-item-time">{{ n.time }}</div>
                </div>
              </el-dropdown-item>
              <div class="notif-footer">
                <el-button link type="primary" size="small">查看全部</el-button>
              </div>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

      </div>
    </div>

    <!-- Tab 标签栏 -->
    <div class="tab-bar" @click="closeTabMenu">
      <div
        v-for="tab in tabs"
        :key="tab.path"
        class="tab-item"
        :class="{ active: activePath === tab.path }"
        @click.stop="onTabClick(tab)"
        @contextmenu.prevent="onTabContextmenu($event, tab)"
      >
        <span class="tab-title">{{ tab.title || tab.meta?.title || '未命名' }}</span>
        <el-icon
          v-if="!tab.meta?.affix && !isLastHomeTab(tab)"
          :size="12"
          class="tab-close"
          @click.stop="onTabRemove(tab.path)"
        >
          <Close />
        </el-icon>
      </div>

      <!-- Tab 右键菜单 -->
      <div
        v-if="tabMenuVisible"
        class="tab-context-menu"
        :style="{ left: tabMenuPosition.x + 'px', top: tabMenuPosition.y + 'px' }"
      >
        <div class="context-menu-item" @click="onTabRemove(selectedTab)">关闭</div>
        <div class="context-menu-item" @click="handleCloseOthers">关闭其他</div>
        <div class="context-menu-item" @click="handleCloseRight">关闭右侧</div>
        <div class="context-menu-item" @click="handleCloseAll">关闭全部</div>
      </div>
    </div>

    <el-dialog
      v-model="searchVisible"
      class="route-search-dialog"
      width="560px"
      :show-close="false"
      :close-on-click-modal="true"
      align-center
      @closed="searchKeyword = ''"
    >
      <div class="route-search">
        <div class="route-search-input">
          <el-icon><Search /></el-icon>
          <input
            ref="searchInputRef"
            v-model="searchKeyword"
            type="search"
            placeholder="搜索菜单、页面或功能…"
            @keydown.enter.prevent="handleSearchEnter"
          />
          <kbd>ESC</kbd>
        </div>
        <div class="route-search-results">
          <button
            v-for="item in searchResults"
            :key="item.path"
            type="button"
            class="route-result"
            @click="navigateToSearchResult(item)"
          >
            <span class="route-icon">
              <el-icon><component :is="item.icon || 'Document'" /></el-icon>
            </span>
            <span class="route-copy">
              <strong>{{ item.title }}</strong>
              <small>{{ item.breadcrumb }}</small>
            </span>
            <el-icon class="route-arrow"><Right /></el-icon>
          </button>
          <div v-if="searchResults.length === 0" class="route-empty">
            没有找到“{{ searchKeyword }}”相关页面
          </div>
        </div>
        <div class="route-search-footer">
          <span><kbd>↵</kbd> 打开首项</span>
          <span>共 {{ searchableRoutes.length }} 个可访问页面</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.navbar-vben {
  background: var(--admin-surface);
  border-bottom: 1px solid var(--admin-border);
}

/* 顶部工具栏 */
.navbar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  gap: 12px;
}

.top-left {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 12px;

  .hamburger {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    cursor: pointer;
    color: var(--admin-text-secondary);
    transition: all 0.2s;

    &:hover {
      background: var(--admin-hover);
      color: #165dff;
    }
  }

  .breadcrumb {
    min-width: 0;
    overflow: hidden;

    :deep(.el-breadcrumb__inner) {
      font-size: 14px;
      white-space: nowrap;
    }
    :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
      color: var(--admin-text);
      font-weight: 500;
    }
  }
}

.top-right {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 4px;

  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--admin-hover);
    border-radius: 6px;
    cursor: pointer;
    color: #86909c;
    font-size: 13px;
    margin-right: 8px;
    transition: all 0.2s;

    &:hover {
      background: var(--admin-border);
    }

    .search-kbd {
      font-size: 11px;
      padding: 1px 6px;
      border-radius: 4px;
      background: var(--admin-surface);
      border: 1px solid var(--admin-border);
      color: #86909c;
      font-family: monospace;
    }
  }

  .tool-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    cursor: pointer;
    color: var(--admin-text-secondary);
    transition: all 0.2s;
    position: relative;

    &:hover {
      background: var(--admin-hover);
      color: #165dff;
    }

    .notification-dot {
      position: absolute;
      top: 2px;
      right: 2px;
      min-width: 16px;
      height: 16px;
      padding: 0 4px;
      background: #f53f3f;
      color: #fff;
      font-size: 10px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
    }
  }

}

/* Tab 标签栏 */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 12px 0;
  background: var(--admin-bg);
  border-top: 1px solid var(--admin-border);
  overflow-x: auto;
  position: relative;

  .tab-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    background: var(--admin-surface);
    border-radius: 8px 8px 0 0;
    cursor: pointer;
    font-size: 13px;
    color: var(--admin-text-secondary);
    border: 1px solid transparent;
    border-bottom: none;
    transition: all 0.2s;
    white-space: nowrap;
    user-select: none;

    &:hover {
      color: #165dff;
    }

    &.active {
      background: var(--admin-bg);
      color: #165dff;
      font-weight: 500;
      border-color: var(--admin-border);
      border-bottom: 1px solid var(--admin-bg);
      margin-bottom: -1px;
    }

    .tab-close {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      padding: 1px;
      transition: all 0.2s;

      &:hover {
        background: #e5e6eb;
        color: #f53f3f;
      }
    }
  }
}

/* Tab 右键菜单 */
.tab-context-menu {
  position: fixed;
  z-index: 3000;
  background: var(--admin-surface);
  border: 1px solid var(--admin-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  min-width: 120px;

  .context-menu-item {
    padding: 8px 16px;
    font-size: 13px;
    color: var(--admin-text-secondary);
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: var(--admin-hover);
      color: #165dff;
    }
  }
}

/* 通知下拉 */
:global(.notification-dropdown-vben) {
  width: 320px !important;
  padding: 0 !important;

  .notif-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #e5e6eb;

    .notif-title {
      font-weight: 600;
      font-size: 14px;
    }
  }

  .notif-item {
    padding: 8px 0;
    width: 100%;

    .notif-item-title {
      font-weight: 500;
      font-size: 13px;
      margin-bottom: 4px;
    }
    .notif-item-desc {
      font-size: 12px;
      color: #86909c;
      margin-bottom: 4px;
    }
    .notif-item-time {
      font-size: 11px;
      color: #c9cdd4;
    }
  }

  .notif-footer {
    padding: 8px;
    text-align: center;
    border-top: 1px solid #e5e6eb;
  }
}

:global(.route-search-dialog) {
  max-width: calc(100vw - 24px);
  overflow: hidden;
  padding: 0 !important;
  border-radius: 14px !important;
  background: var(--admin-surface) !important;
}

@media (max-width: 900px) {
  .navbar-top {
    padding: 0 10px;
  }

  .top-left {
    gap: 6px;
  }

  .top-right {
    gap: 1px;

    .search-box {
      width: 32px;
      height: 32px;
      justify-content: center;
      margin-right: 2px;
      padding: 0;

      .search-text,
      .search-kbd {
        display: none;
      }
    }
  }
}

@media (max-width: 640px) {
  .breadcrumb {
    display: none;
  }

  .navbar-top {
    height: 50px;
  }

  .top-right .tool-btn {
    width: 30px;
    height: 30px;
  }

  .tab-bar {
    padding-left: 8px;
    padding-right: 8px;
  }
}

:global(.route-search-dialog .el-dialog__header) {
  display: none;
}

:global(.route-search-dialog .el-dialog__body) {
  padding: 0;
}

.route-search {
  color: var(--admin-text);
}

.route-search-input {
  display: flex;
  height: 60px;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid var(--admin-border);
  color: var(--admin-text-secondary);

  input {
    min-width: 0;
    flex: 1;
    border: 0;
    outline: 0;
    color: var(--admin-text);
    background: transparent;
    font-size: 15px;
  }

  kbd {
    padding: 2px 6px;
    border: 1px solid var(--admin-border);
    border-radius: 5px;
    background: var(--admin-hover);
    font-size: 10px;
  }
}

.route-search-results {
  max-height: 420px;
  overflow-y: auto;
  padding: 8px;
}

.route-result {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 10px 12px;
  border: 0;
  border-radius: 9px;
  color: var(--admin-text);
  background: transparent;
  text-align: left;

  &:hover {
    background: var(--admin-hover);
  }
}

.route-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 8px;
  color: #409eff;
  background: rgba(64, 158, 255, 0.12);
}

.route-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;

  strong {
    font-size: 14px;
  }

  small {
    overflow: hidden;
    margin-top: 3px;
    color: var(--admin-text-muted);
    white-space: nowrap;
    text-overflow: ellipsis;
    font-size: 11px;
  }
}

.route-arrow {
  color: var(--admin-text-muted);
}

.route-empty {
  padding: 48px 20px;
  color: var(--admin-text-muted);
  text-align: center;
}

.route-search-footer {
  display: flex;
  justify-content: space-between;
  padding: 9px 18px;
  border-top: 1px solid var(--admin-border);
  color: var(--admin-text-muted);
  background: var(--admin-bg);
  font-size: 11px;
}

:global(.dark) {
  .navbar-vben {
    border-color: var(--admin-border);
    background: var(--admin-surface);
  }

  .top-left .breadcrumb :deep(.el-breadcrumb__inner),
  .top-left .breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
    color: var(--admin-text-secondary);
  }

  .top-right .search-box,
  .top-right .tool-btn {
    color: var(--admin-text-secondary);
  }

  .top-right .search-box,
  .top-right .tool-btn:hover,
  .top-left .hamburger:hover {
    background: var(--admin-hover);
  }

  .top-right .search-box .search-kbd {
    border-color: var(--admin-border);
    color: var(--admin-text-muted);
    background: var(--admin-surface);
  }

  .tab-bar {
    border-color: var(--admin-border);
    background: var(--admin-bg);
  }

  .tab-bar .tab-item {
    color: var(--admin-text-secondary);
    background: var(--admin-surface);

    &.active {
      border-color: var(--admin-border);
      color: #79bbff;
      background: var(--admin-bg);
    }
  }

  .tab-context-menu {
    border-color: var(--admin-border);
    background: var(--admin-surface);
  }
}
</style>
