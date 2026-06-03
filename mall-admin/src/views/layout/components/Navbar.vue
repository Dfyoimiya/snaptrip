<script lang="ts" setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Fold, Expand, Search, RefreshRight, FullScreen,
  Bell, Setting, ArrowDown, SwitchButton, UserFilled,
  Close, CloseBold, CircleCloseFilled, Moon, Sunny,
} from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { useTabStore } from '@/stores/tab'
import type { TabView } from '@/stores/tab'

const appStore = useAppStore()
const userStore = useUserStore()
const tabStore = useTabStore()
const route = useRoute()
const router = useRouter()

const sidebar = computed(() => appStore.sidebar)
const username = computed(() => userStore.username)
const avatar = computed(() => userStore.avatar)
const tabs = computed(() => tabStore.tabList)
const activePath = computed(() => route.path)

// 面包屑
const breadcrumbs = computed(() => {
  return route.matched.filter((item) => item.meta && item.meta.title)
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
function goHome() { router.push('/') }

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

// 用户命令
function handleCommand(command: string) {
  if (command === 'logout') {
    userStore.logout().then(() => router.push('/login'))
  } else if (command === 'home') {
    goHome()
  }
}

// Tab 操作
function onTabClick(tab: TabView) {
  router.push(tab.fullPath)
}
function onTabRemove(path: string) {
  const isActive = path === route.path
  tabStore.removeView(path)
  if (isActive && tabs.value.length > 0) {
    router.push(tabs.value[tabs.value.length - 1].fullPath)
  }
}

// Tab 右键菜单
function onTabContextmenu(e: MouseEvent, tab: TabView) {
  e.preventDefault()
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
    router.push('/')
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
        <div class="search-box">
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
        <div class="tool-btn" title="主题">
          <el-icon :size="16"><Moon /></el-icon>
        </div>
        <div class="tool-btn" title="设置">
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

        <!-- 用户 -->
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <img :src="avatar" class="user-avatar" alt="avatar" />
            <span class="user-name">{{ username }}</span>
            <el-icon :size="12"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="home">
                <el-icon><UserFilled /></el-icon> 个人中心
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
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
          v-if="!tab.meta?.affix"
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
  </div>
</template>

<style lang="scss" scoped>
.navbar-vben {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}

/* 顶部工具栏 */
.navbar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
}

.top-left {
  display: flex;
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
    color: #606266;
    transition: all 0.2s;

    &:hover {
      background: #f2f3f5;
      color: #165dff;
    }
  }

  .breadcrumb {
    :deep(.el-breadcrumb__inner) {
      font-size: 14px;
    }
    :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
      color: #1f2229;
      font-weight: 500;
    }
  }
}

.top-right {
  display: flex;
  align-items: center;
  gap: 4px;

  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: #f2f3f5;
    border-radius: 6px;
    cursor: pointer;
    color: #86909c;
    font-size: 13px;
    margin-right: 8px;
    transition: all 0.2s;

    &:hover {
      background: #e5e6eb;
    }

    .search-kbd {
      font-size: 11px;
      padding: 1px 6px;
      border-radius: 4px;
      background: #fff;
      border: 1px solid #e5e6eb;
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
    color: #606266;
    transition: all 0.2s;
    position: relative;

    &:hover {
      background: #f2f3f5;
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

  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 6px;
    margin-left: 4px;

    &:hover {
      background: #f2f3f5;
    }

    .user-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
    }

    .user-name {
      font-size: 14px;
      color: #1f2229;
    }
  }
}

/* Tab 标签栏 */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 12px 0;
  background: #f0f2f5;
  border-top: 1px solid #e8e8e8;
  overflow-x: auto;
  position: relative;

  .tab-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    background: #fff;
    border-radius: 8px 8px 0 0;
    cursor: pointer;
    font-size: 13px;
    color: #4e5969;
    border: 1px solid transparent;
    border-bottom: none;
    transition: all 0.2s;
    white-space: nowrap;
    user-select: none;

    &:hover {
      color: #165dff;
    }

    &.active {
      background: #f7f8fa;
      color: #165dff;
      font-weight: 500;
      border-color: #e8e8e8;
      border-bottom: 1px solid #f7f8fa;
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
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  min-width: 120px;

  .context-menu-item {
    padding: 8px 16px;
    font-size: 13px;
    color: #4e5969;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: #f2f3f5;
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
</style>
