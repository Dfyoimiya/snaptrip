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
}>()

const emit = defineEmits<{
  /** 导航事件 */
  (e: 'navigate', path: string): void
  /** 退出登录事件 */
  (e: 'logout'): void
}>()

/** 快捷入口菜单 */
const quickLinks = [
  { label: '我的订单', path: '/orders', requireAuth: true },
  { label: '会员中心', path: '/member', requireAuth: true },
  { label: '我的收藏', path: '/favorites', requireAuth: true },
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
  <div class="bg-gray-800 text-gray-300">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-9 text-xs">
        <!-- 左侧：欢迎语 -->
        <div class="flex items-center gap-2">
          <template v-if="isLoggedIn">
            <span>欢迎，</span>
            <span class="text-white font-medium">{{ displayName }}</span>
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
              class="px-2 py-1 hover:text-white transition-colors"
              @click="handleLogin"
            >
              登录
            </button>
            <span class="text-gray-600">|</span>
            <button
              class="px-2 py-1 hover:text-white transition-colors"
              @click="handleRegister"
            >
              注册
            </button>
          </template>

          <!-- 已登录状态：退出 -->
          <template v-else>
            <button
              class="px-2 py-1 hover:text-white transition-colors"
              @click="handleLogout"
            >
              退出登录
            </button>
          </template>

          <!-- 分隔符 -->
          <span class="text-gray-600 mx-1">|</span>

          <!-- 快捷入口 -->
          <button
            v-for="(link, index) in filteredLinks"
            :key="link.path"
            class="px-2 py-1 hover:text-white transition-colors"
            @click="handleNavigate(link.path)"
          >
            {{ link.label }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
