<script setup lang="ts">
/**
 * ============================================
 * 左侧浮动导航栏 (LeftSidebar) — 玻璃拟态风格
 *
 * hover 展开 / 点击锁定，折叠态仅显示图标。
 * 毛玻璃半透效果，position: fixed 浮动于页面之上。
 * ============================================
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useMemberStore } from '@/stores/member'
import { useLayoutStore } from '@/stores/layout'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const memberStore = useMemberStore()
const layoutStore = useLayoutStore()

const expanded = computed(() => layoutStore.leftSidebarExpanded || layoutStore.leftSidebarLocked)
const locked = computed(() => layoutStore.leftSidebarLocked)

interface NavGroup {
  title?: string
  items: NavItem[]
}

interface NavItem {
  path: string
  label: string
  badge?: () => string | null
}

const cartBadge = computed(() => {
  const count = cartStore.totalCount
  if (count <= 0) return null
  return count > 99 ? '99+' : String(count)
})

const compareCount = computed(() => {
  const n = layoutStore.compareProducts.length
  return n > 0 ? String(n) : null
})

const coreGroup: NavGroup = {
  items: [
    { path: '/', label: '首页' },
    { path: '/shopping-guide', label: '帮我挑' },
    { path: '/notice', label: '消息' },
    { path: '/cart', label: '购物车', badge: () => cartBadge.value },
    { path: '/member/orders', label: '订单' },
  ],
}

const contentGroup: NavGroup = {
  title: '频道',
  items: [
    { path: '/discover', label: '逛一逛' },
    { path: '/category', label: '采购宝' },
    { path: '/hot', label: '人气推荐' },
    { path: '/new', label: '新品上架' },
    { path: '/brand', label: '品牌专区' },
    { path: '/shopping-guide', label: '直播' },
    { path: '/member/favorites', label: '收藏' },
  ],
}

const bottomGroup: NavGroup = {
  items: [
    { path: '/member/settings', label: '外观' },
    { path: '/help', label: '帮助' },
  ],
}

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  if (path === '/category') {
    return route.path === '/category' || route.path === '/search' || route.path.startsWith('/product/')
  }
  if (path === '/member/orders') return route.path === '/member/orders'
  if (path === '/member/favorites') return route.path === '/member/favorites'
  if (path === '/member/settings') return route.path === '/member/settings'
  return route.path === path || route.path.startsWith(`${path}/`)
}

function navigate(path: string) {
  if (path === '/member/orders' || path === '/member/favorites' || path === '/member/settings') {
    if (!memberStore.isLoggedIn) {
      router.push('/login')
      return
    }
  }
  router.push(path)
}

function handleLogout() {
  cartStore.clearCart()
  memberStore.memberLogout()
  router.push('/')
}

function handleCompareClick() {
  if (layoutStore.compareProducts.length >= 2) {
    layoutStore.startCompare()
  }
}

// ── hover / lock ──
function onMouseEnter() {
  layoutStore.leftSidebarExpanded = true
}
function onMouseLeave() {
  if (!layoutStore.leftSidebarLocked) {
    layoutStore.leftSidebarExpanded = false
  }
}
function toggleLock() {
  if (layoutStore.leftSidebarLocked) {
    layoutStore.unlockLeftSidebar()
  } else {
    layoutStore.lockLeftSidebar()
  }
}
</script>

<template>
  <aside
    class="left-sidebar"
    :class="{ expanded: expanded, locked: locked }"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <!-- Logo -->
    <router-link to="/" class="logo-area" title="首页">
      <div class="logo-icon-box">
        <svg
          class="logo-icon-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
        </svg>
      </div>
      <div v-show="expanded" class="logo-text-group">
        <span class="logo-text">MALL</span>
        <span class="logo-sub">正品好货</span>
      </div>
    </router-link>

    <!-- 可滚动中间区域 -->
    <div class="scrollable-area">
      <!-- 核心导航 -->
      <nav class="nav-section">
        <button
          v-for="item in coreGroup.items"
          :key="item.path + item.label"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="navigate(item.path)"
          :title="item.label"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge?.()" class="nav-badge" :class="{ collapsed: !expanded }">{{ item.badge() }}</span>
        </button>
      </nav>

      <!-- 分隔线 -->
      <div class="nav-divider" />

      <!-- 内容频道 -->
      <div class="nav-section with-title">
        <div v-show="expanded" class="section-title">{{ contentGroup.title }}</div>
        <button
          v-for="item in contentGroup.items"
          :key="item.path + item.label"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="navigate(item.path)"
          :title="item.label"
        >
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </div>
    </div>

    <!-- 底部工具 -->
    <div class="bottom-section">
      <!-- 商品对比入口 -->
      <button
        v-if="layoutStore.compareProducts.length > 0"
        class="nav-item compare-entry"
        @click="handleCompareClick"
        title="商品对比"
      >
        <span class="nav-label">商品对比</span>
        <span class="nav-badge compare-badge" :class="{ collapsed: !expanded }">{{ compareCount }}</span>
      </button>

      <button
        v-for="item in bottomGroup.items"
        :key="item.path + item.label"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        @click="navigate(item.path)"
        :title="item.label"
      >
        <span class="nav-label">{{ item.label }}</span>
      </button>

      <button v-if="memberStore.isLoggedIn" class="nav-item logout-item" @click="handleLogout" title="退出">
        <span class="nav-label">退出</span>
      </button>

      <!-- 锁定按钮 -->
      <button class="nav-item lock-toggle" @click="toggleLock" :title="locked ? '取消固定' : '固定侧边栏'">
        <span class="nav-label lock-label">{{ locked ? '已固定' : '固定' }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
/* ============================================
   玻璃拟态浮动侧边栏
   ============================================ */
.left-sidebar {
  position: fixed;
  top: 12px;
  left: 12px;
  bottom: 12px;
  width: 64px;
  height: calc(100vh - 24px);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
  z-index: 50;
  overflow: hidden;
  transition: width 0.2s ease;
}

.left-sidebar.expanded {
  width: 200px;
}

/* ============================================
   Logo
   ============================================ */
.logo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 0 12px;
  text-decoration: none;
  flex-shrink: 0;
}

.logo-icon-box {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #ff5000, #ff7900);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.logo-icon-svg {
  width: 20px;
  height: 20px;
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.logo-text {
  font-size: 13px;
  font-weight: 700;
  color: #1f1f1f;
  letter-spacing: 0.05em;
}

.logo-sub {
  font-size: 9px;
  color: #999;
  letter-spacing: 0.08em;
}

/* ============================================
   可滚动中间区域
   ============================================ */
.scrollable-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 8px 4px;
  scrollbar-width: none;
}

.scrollable-area::-webkit-scrollbar {
  display: none;
}

/* ============================================
   分隔线
   ============================================ */
.nav-divider {
  height: 1px;
  margin: 8px 4px;
  background: rgba(0, 0, 0, 0.06);
}

/* ============================================
   导航区块
   ============================================ */
.nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-section.with-title {
  padding-top: 0;
}

.section-title {
  font-size: 10px;
  color: #999;
  padding: 0 6px 8px;
  text-align: center;
  letter-spacing: 0.05em;
}

/* ============================================
   导航项
   ============================================ */
.nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 8px;
  border-radius: 8px;
  font-size: 12px;
  color: #555;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: center;
  transition: background-color 0.15s, color 0.15s;
  user-select: none;
  position: relative;
  white-space: nowrap;
}

.left-sidebar.expanded .nav-item {
  justify-content: flex-start;
  text-align: left;
}

.nav-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
  color: #1f1f1f;
}

.nav-item.active {
  background-color: rgba(255, 80, 0, 0.1);
  color: #ff5000;
  font-weight: 600;
}

.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.nav-badge {
  position: absolute;
  top: 4px;
  right: 2px;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border-radius: 7px;
  background: #ff5000;
  color: #fff;
  font-size: 9px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* 折叠态角标缩小为圆点 */
.nav-badge.collapsed {
  min-width: 7px;
  width: 7px;
  height: 7px;
  padding: 0;
  top: 6px;
  right: 6px;
  border-radius: 50%;
  font-size: 0;
}

/* ============================================
   底部工具区
   ============================================ */
.bottom-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 8px 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

/* ============================================
   退出按钮
   ============================================ */
.logout-item:hover {
  background-color: rgba(220, 38, 38, 0.08);
  color: #dc2626;
}

/* ============================================
   对比入口
   ============================================ */
.compare-entry {
  color: #7c3aed;
}

.compare-entry:hover {
  background-color: rgba(124, 58, 237, 0.08);
  color: #6d28d9;
}

.compare-badge {
  background: #7c3aed;
}

/* ============================================
   锁定按钮
   ============================================ */
.lock-toggle {
  margin-top: 4px;
  font-size: 11px;
  color: #aaa;
}

.lock-toggle:hover {
  color: #888;
}

.lock-label {
  font-size: 10px;
}
</style>
