<script setup lang="ts">
/**
 * ============================================
 * 左侧浮动导航栏 (LeftSidebar) — 玻璃拟态风格
 *
 * 与 B 端统一的玻璃拟态卡片结构，保留商城橙色品牌语义。
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

interface NavGroup {
  title?: string
  items: NavItem[]
}

interface NavItem {
  path: string
  label: string
  iconPath: string
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
    { path: '/', label: '首页', iconPath: 'M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10.5Z' },
    { path: '/shopping-guide', label: '帮我挑', iconPath: 'M9.5 4.5a6 6 0 1 1-1.68 11.76L4 20l1.24-4.34A6 6 0 0 1 9.5 4.5Zm7.5 1a4.5 4.5 0 0 1 2.9 7.94L21 17l-3.23-1.08' },
    { path: '/chat', label: '消息', iconPath: 'M4 5h16v12H8l-4 4V5Zm4 4h8M8 13h5' },
    { path: '/member/orders', label: '订单', iconPath: 'M6 3h12v18l-3-2-3 2-3-2-3 2V3Zm3 5h6m-6 4h6' },
  ],
}

const contentGroup: NavGroup = {
  title: '频道',
  items: [
    { path: '/discover', label: '逛一逛', iconPath: 'M12 3 9.5 9.5 3 12l6.5 2.5L12 21l2.5-6.5L21 12l-6.5-2.5L12 3Z' },
    { path: '/category', label: '采购宝', iconPath: 'M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z' },
    { path: '/hot', label: '人气推荐', iconPath: 'M13 3s1 4-2 6c-2.5 1.7-3 4-1 6 0-2 1-3 2-4 0 3 3 4 2 7 3-1 5-3.5 5-6.5C19 7 15 5 13 3ZM8 8c-2 2-3 4-3 6.5A6.5 6.5 0 0 0 11.5 21' },
    { path: '/new', label: '新品上架', iconPath: 'M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4' },
    { path: '/member/favorites', label: '收藏', iconPath: 'M12 20.5 4.7 13.7A5 5 0 0 1 12 6.9a5 5 0 0 1 7.3 6.8L12 20.5Z' },
  ],
}

const bottomGroup: NavGroup = {
  items: [
    { path: '/help', label: '帮助中心', iconPath: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm-3-13a3 3 0 1 1 4.4 2.65c-.9.45-1.4 1.05-1.4 2.35m0 4h.01' },
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

function handleCompareClick() {
  if (layoutStore.compareProducts.length >= 2) {
    layoutStore.startCompare()
  }
}

function handleAccountClick() {
  router.push(memberStore.isLoggedIn ? '/member' : '/login')
}
</script>

<template>
  <aside class="left-sidebar">
    <div class="brand-row">
      <router-link to="/" class="brand-link" title="首页">
        <span class="brand-mark">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M16 11V7a4 4 0 0 0-8 0v4M5 9h14l1 12H4L5 9Z" />
          </svg>
        </span>
        <span class="brand-name">SnapTrip</span>
      </router-link>
    </div>

    <div class="workspace-row">
      <button class="workspace-trigger" type="button" @click="navigate('/discover')">
        <span class="workspace-avatar">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z" />
          </svg>
        </span>
        <span class="workspace-copy">
          <strong>SnapTrip 商城</strong>
          <small>发现你的品质好物</small>
        </span>
        <svg class="workspace-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>
    </div>

    <div class="menu-caption">快捷入口</div>

    <!-- 可滚动中间区域 -->
    <div class="scrollable-area">
      <nav class="nav-section">
        <button
          v-for="item in coreGroup.items"
          :key="item.path + item.label"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :title="item.label"
          @click="navigate(item.path)"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path :d="item.iconPath" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge?.()" class="nav-badge">{{ item.badge() }}</span>
        </button>
      </nav>

      <div class="menu-caption inner-caption">{{ contentGroup.title }}</div>

      <nav class="nav-section">
        <button
          v-for="item in contentGroup.items"
          :key="item.path + item.label"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :title="item.label"
          @click="navigate(item.path)"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path :d="item.iconPath" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>
    </div>

    <div class="bottom-section">
      <button
        v-if="layoutStore.compareProducts.length > 0"
        class="nav-item compare-entry"
        type="button"
        @click="handleCompareClick"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M8 4 4 8l4 4M4 8h12m0 4 4 4-4 4m4-4H8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span class="nav-label">商品对比</span>
        <span class="nav-badge compare-badge">{{ compareCount }}</span>
      </button>

      <button
        class="nav-item theme-toggle"
        type="button"
        :title="layoutStore.theme === 'light' ? '切换到黑暗模式' : '切换到光亮模式'"
        :aria-label="layoutStore.theme === 'light' ? '切换到黑暗模式' : '切换到光亮模式'"
        @click="layoutStore.toggleTheme"
      >
        <svg
          class="nav-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <template v-if="layoutStore.theme === 'light'">
            <path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z" />
          </template>
          <template v-else>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
          </template>
        </svg>
        <span class="nav-label">
          {{ layoutStore.theme === 'light' ? '黑暗模式' : '光亮模式' }}
        </span>
        <span class="theme-status">{{ layoutStore.theme === 'light' ? '暗' : '亮' }}</span>
      </button>

      <button
        v-for="item in bottomGroup.items"
        :key="item.path + item.label"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        @click="navigate(item.path)"
        :title="item.label"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path :d="item.iconPath" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span class="nav-label">{{ item.label }}</span>
      </button>

      <div class="account-cart-panel">
        <button class="account-trigger" type="button" @click="handleAccountClick">
          <span class="account-avatar">{{ memberStore.isLoggedIn ? '我' : '客' }}</span>
          <span class="account-copy">
            <strong>{{ memberStore.isLoggedIn ? '个人中心' : '登录账户' }}</strong>
            <small>{{ memberStore.isLoggedIn ? '查看订单与权益' : '登录后享受完整服务' }}</small>
          </span>
          <svg class="account-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
        <button
          v-if="memberStore.isLoggedIn"
          class="account-cart-trigger"
          type="button"
          :class="{ active: isActive('/cart') }"
          aria-label="打开购物车"
          @click="navigate('/cart')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M3 4h2l2.4 10.2a2 2 0 0 0 1.95 1.54H18a2 2 0 0 0 1.94-1.52L21 8H6m4 12h.01M18 20h.01" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span v-if="cartBadge" class="account-cart-badge">{{ cartBadge }}</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.left-sidebar {
  position: fixed;
  top: 48px;
  left: 12px;
  bottom: 12px;
  z-index: 50;
  display: flex;
  width: 184px;
  height: calc(100vh - 60px);
  flex-direction: column;
  overflow: hidden;
  color: var(--mall-text-secondary);
  background: var(--mall-glass-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--mall-glass-border);
  border-radius: 16px;
  box-shadow: var(--mall-glass-shadow);
  transition: color 0.2s ease, background-color 0.2s ease;
}

.brand-row {
  display: flex;
  height: 48px;
  flex-shrink: 0;
  align-items: center;
  padding: 0 10px;
  border-bottom: 1px solid var(--mall-border);
}

.brand-link {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  color: var(--mall-text);
  text-decoration: none;
}

.brand-mark,
.workspace-avatar {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, #ff5000, #ff7900);
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  box-shadow: 0 6px 16px rgba(255, 80, 0, 0.24);

  svg {
    width: 16px;
    height: 16px;
  }
}

.brand-name {
  white-space: nowrap;
  font-size: 15px;
  font-weight: 750;
  letter-spacing: -0.3px;
}

.workspace-row {
  padding: 8px 6px 4px;
}

.workspace-trigger,
.account-trigger {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  border: 0;
  color: var(--mall-text);
  background: transparent;
  text-align: left;
  transition: background 0.18s ease;

  &:hover {
    background: var(--mall-hover);
  }
}

.account-cart-panel:not(:has(.account-cart-trigger)) .account-trigger {
  width: 100%;
}

.workspace-trigger {
  height: 44px;
  padding: 4px 6px;
  border-radius: 9px;
}

.workspace-avatar {
  width: 28px;
  height: 28px;
  border-radius: 7px;

  svg {
    width: 14px;
    height: 14px;
  }
}

.workspace-copy,
.account-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  line-height: 1.25;

  strong {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    font-size: 12px;
    font-weight: 650;
  }

  small {
    overflow: hidden;
    margin-top: 2px;
    color: var(--mall-text-muted);
    white-space: nowrap;
    text-overflow: ellipsis;
    font-size: 10px;
  }
}

.workspace-chevron,
.account-chevron {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  color: var(--mall-text-muted);
}

.menu-caption {
  padding: 8px 14px 4px;
  color: var(--mall-text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

.inner-caption {
  padding-top: 12px;
}

.scrollable-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 6px 6px;
  scrollbar-width: none;
}

.scrollable-area::-webkit-scrollbar {
  display: none;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  position: relative;
  display: flex;
  width: 100%;
  height: 36px;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  padding: 0 9px;
  border: 0;
  border-radius: 8px;
  color: var(--mall-text-secondary);
  background: transparent;
  white-space: nowrap;
  text-align: left;
  transition: background-color 0.15s, color 0.15s;
  user-select: none;
}

.nav-item:hover {
  color: var(--mall-text);
  background: var(--mall-hover);
}

.nav-item.active {
  color: #ff5000;
  background: rgba(255, 80, 0, 0.1);
  font-weight: 650;
}

.nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.nav-badge {
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

.bottom-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px;
  border-top: 1px solid var(--mall-border);
}

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

.theme-toggle {
  margin-top: 1px;
}

.theme-status {
  display: grid;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 6px;
  color: var(--mall-text-muted);
  background: var(--mall-hover);
  font-size: 10px;
  font-weight: 700;
}

.account-trigger {
  min-width: 0;
  flex: 1;
  height: 44px;
  padding: 0 7px;
  border-radius: 9px;
}

.account-cart-panel {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  padding: 3px;
  border: 1px solid var(--mall-border);
  border-radius: 12px;
  background: var(--mall-surface);
}

.account-cart-trigger {
  position: relative;
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 9px;
  color: var(--mall-text-secondary);
  background: var(--mall-hover);
  transition: color 0.15s, background-color 0.15s;
}

.account-cart-trigger:hover,
.account-cart-trigger.active {
  color: #ff5000;
  background: rgba(255, 80, 0, 0.1);
}

.account-cart-trigger svg {
  width: 18px;
  height: 18px;
}

.account-cart-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  display: grid;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  place-items: center;
  border: 2px solid var(--mall-surface);
  border-radius: 8px;
  color: #fff;
  background: #ff5000;
  font-size: 8px;
  font-weight: 700;
}

.account-avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, #ff7900, #ff5000);
  font-size: 11px;
  font-weight: 700;
}

@media (max-width: 1023px) {
  .left-sidebar {
    display: none;
  }
}
</style>
