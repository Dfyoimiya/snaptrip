<script setup lang="ts">
/**
 * ============================================
 * 顶部通栏导航条组件 (TopBar)
 * 包含：欢迎语 | 登录/注册 | 我的订单 | 会员中心
 * ============================================
 */
import { computed } from 'vue'

const props = defineProps<{
  /** 是否已登录 */
  isLoggedIn: boolean
  /** 用户显示名称 */
  displayName: string
  /** 购物车数量 */
  cartCount: number
}>()

const emit = defineEmits<{
  /** 导航事件 */
  (e: 'navigate', path: string): void
  /** 退出登录事件 */
  (e: 'logout'): void
}>()

/** 快捷入口菜单 */
const quickLinks = [
  { label: '我的订单', path: '/member/orders', requireAuth: true },
  { label: '浏览记录', path: '/member/history', requireAuth: true },
  { label: '领券中心', path: '/coupons', requireAuth: false },
  { label: '我的收藏', path: '/member/favorites', requireAuth: true },
  { label: '会员中心', path: '/member', requireAuth: true },
  { label: '帮助中心', path: '/help', requireAuth: false },
]

/** 过滤后的快捷入口（未登录时隐藏需认证的入口） */
const filteredLinks = computed(() =>
  quickLinks.filter((link) => {
    if (!link.requireAuth) return true
    return props.isLoggedIn
  }),
)

const handleNavigate = (path: string) => {
  emit('navigate', path)
}

const handleLogin = () => {
  emit('navigate', '/login')
}

const handleRegister = () => {
  emit('navigate', '/register')
}

const handleLogout = () => {
  emit('logout')
}
</script>

<template>
  <div class="bg-white text-gray-500">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-9 text-xs">
        <!-- 左侧：欢迎语 -->
        <div class="flex items-center gap-2">
          <template v-if="isLoggedIn">
            <span>欢迎，</span>
            <span class="text-gray-800 font-medium">{{ displayName }}</span>
          </template>
          <template v-else>
            <span>欢迎来到商城！</span>
          </template>
        </div>

        <!-- 右侧：操作入口 -->
        <div class="flex items-center gap-1">
          <!-- 未登录状态：登录 | 注册 -->
          <template v-if="!isLoggedIn">
            <button
              class="px-2 py-1 hover:text-gray-800 transition-colors"
              @click="handleLogin"
            >
              登录
            </button>
            <span class="text-gray-300">|</span>
            <button
              class="px-2 py-1 hover:text-gray-800 transition-colors"
              @click="handleRegister"
            >
              注册
            </button>
          </template>

          <!-- 已登录状态：退出 -->
          <template v-else>
            <button
              class="px-2 py-1 hover:text-gray-800 transition-colors"
              @click="handleLogout"
            >
              退出登录
            </button>
          </template>

          <!-- 购物车 -->
          <button
            class="px-2 py-1 hover:text-brand-600 transition-colors flex items-center gap-1"
            @click="emit('navigate', '/cart')"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            购物车
            <span
              v-if="cartCount > 0"
              class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-brand-600 text-white text-[10px] font-medium rounded-full"
            >{{ cartCount > 99 ? '99+' : cartCount }}</span>
          </button>

          <!-- 分隔符 -->
          <span class="text-gray-300 mx-1">|</span>

          <!-- 快捷入口 -->
          <button
            v-for="(link, index) in filteredLinks"
            :key="link.path"
            class="px-2 py-1 hover:text-gray-800 transition-colors"
            @click="handleNavigate(link.path)"
          >
            {{ link.label }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
