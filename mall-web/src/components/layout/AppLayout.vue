<script setup lang="ts">
/**
 * ============================================
 * 全局布局组件 (Global Layout)
 * PC 端电商网页通用布局：
 * 1. 顶部通栏导航条
 * 2. Logo + 搜索框 + 购物车
 * 3. 主体内容区 (max-w-7xl 居中)
 * 4. 页脚
 * ============================================
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { useCartStore } from '@/stores/cart'
import { useChatStore } from '@/stores/chat'
import TopBar from './TopBar.vue'
import HeaderSearch from './HeaderSearch.vue'

const router = useRouter()
const route = useRoute()
const memberStore = useMemberStore()
const chatStore = useChatStore()
const cartStore = useCartStore()

/** 是否已登录 */
const isLoggedIn = computed(() => memberStore.isLoggedIn)
/** 购物车商品数量 */
const cartCount = computed(() => cartStore.totalCount)

/**
 * 导航到页面
 */
const navigateTo = (path: string) => {
  router.push(path)
}

/**
 * 退出登录
 */
const handleLogout = () => {
  memberStore.memberLogout()
  cartStore.clearCart()
  router.push('/')
}

/** 主导航菜单 */
const navMenus = [
  { label: '首页', path: '/' },
  { label: '全部商品', path: '/category' },
  { label: '品牌专区', path: '/brand' },
  { label: '新品上架', path: '/new' },
  { label: '人气推荐', path: '/hot' },
]

const isMenuActive = (path: string): boolean => {
  if (path === '/') return route.path === '/'
  if (path === '/category') {
    return route.path === '/category' || route.path === '/search' || route.path.startsWith('/product/')
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <div class="min-h-screen flex flex-col mall-shell">
    <!-- 1. 顶部通栏导航条 -->
    <TopBar
      :is-logged-in="isLoggedIn"
      :display-name="memberStore.displayName"
      @navigate="navigateTo"
      @logout="handleLogout"
    />

    <!-- 2. Logo + 搜索框 + 购物车 -->
    <HeaderSearch
      :cart-count="cartCount"
      @navigate="navigateTo"
    />

    <!-- 3. 主导航栏 -->
    <nav class="mall-nav">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center gap-2 h-12 overflow-x-auto">
          <button
            class="category-trigger"
            :class="{ active: isMenuActive('/category') }"
            @click="navigateTo('/category')"
          >
            <span>☰</span> 全部分类
          </button>
          <button
            v-for="menu in navMenus"
            :key="menu.path"
            class="nav-menu-item"
            :class="{ active: isMenuActive(menu.path) }"
            :aria-current="isMenuActive(menu.path) ? 'page' : undefined"
            @click="navigateTo(menu.path)"
          >
            {{ menu.label }}
          </button>
        </div>
      </div>
    </nav>

    <!-- 4. 主体内容区 -->
    <main class="flex-1">
      <div class="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-5">
        <slot />
      </div>
    </main>

    <!-- 5. 页脚 -->
    <footer class="bg-white border-t border-gray-100 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
          <!-- 关于我们 -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">关于我们</h3>
            <ul class="space-y-2">
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/about')">公司简介</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/contact')">联系我们</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/join')">加入我们</button></li>
            </ul>
          </div>
          <!-- 购物指南 -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">购物指南</h3>
            <ul class="space-y-2">
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">购物流程</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">支付方式</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">配送说明</button></li>
            </ul>
          </div>
          <!-- 售后服务 -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">售后服务</h3>
            <ul class="space-y-2">
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">退换货政策</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">退款说明</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">取消订单</button></li>
            </ul>
          </div>
          <!-- 客户服务 -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">客户服务</h3>
            <ul class="space-y-2">
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">常见问题</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="chatStore.openChat()">在线客服</button></li>
              <li><button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="navigateTo('/help')">投诉建议</button></li>
            </ul>
          </div>
        </div>

        <!-- 底部版权 -->
        <div class="mt-8 pt-8 border-t border-gray-200">
          <p class="text-center text-xs text-gray-400">
            &copy; 2026 SnapTrip. 智能推荐驱动的品质商城
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.mall-shell {
  background: #ffffff;
}

.mall-nav {
  background: #ffffff;
  border-bottom: 1px solid #f5f5f5;
  position: sticky;
  top: 0;
  z-index: 30;
}

.category-trigger {
  align-self: stretch;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 24px;
  color: #333;
  background: transparent;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  transition: color 0.2s;
}

.category-trigger:hover,
.category-trigger.active {
  color: #ff5000;
}

.nav-menu-item {
  padding: 8px 18px;
  color: #333;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  transition: color 0.2s;
}

.nav-menu-item:hover,
.nav-menu-item.active {
  color: #ff5000;
}
</style>
