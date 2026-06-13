<script setup lang="ts">
/**
 * ============================================
 * 头部搜索区组件 (HeaderSearch)
 * 包含：Logo | 搜索框 | 购物车入口
 * ============================================
 */
import { ref } from 'vue'

const props = defineProps<{
  /** 购物车商品数量 */
  cartCount: number
}>()

const emit = defineEmits<{
  /** 导航事件 */
  (e: 'navigate', path: string): void
}>()

/** 搜索关键词 */
const keyword = ref('')

/** 热门搜索推荐 */
const hotKeywords = ['手机', '笔记本电脑', '耳机', '运动鞋', '手表']

/**
 * 执行搜索
 */
const handleSearch = () => {
  const kw = keyword.value.trim()
  if (kw) {
    emit('navigate', `/search?keyword=${encodeURIComponent(kw)}`)
  }
}

/**
 * 按回车搜索
 */
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    handleSearch()
  }
}

/**
 * 点击热门标签搜索
 */
const handleHotSearch = (kw: string) => {
  keyword.value = kw
  emit('navigate', `/search?keyword=${encodeURIComponent(kw)}`)
}

/**
 * 跳转到购物车
 */
const handleGoCart = () => {
  emit('navigate', '/cart')
}

/**
 * 跳转到首页
 */
const handleGoHome = () => {
  emit('navigate', '/')
}
</script>

<template>
  <div class="bg-white border-b border-gray-100">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between py-5 gap-8">
        <!-- Logo -->
        <div class="flex-shrink-0 cursor-pointer" @click="handleGoHome">
          <div class="flex items-center gap-3">
            <!-- Logo 图标 -->
            <div class="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-6 w-6 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
                />
              </svg>
            </div>
            <!-- Logo 文字 -->
            <div>
              <h1 class="text-xl font-bold text-gray-900 tracking-tight">MALL</h1>
              <p class="text-[10px] text-gray-400 -mt-1 tracking-wider">正品好货</p>
            </div>
          </div>
        </div>

        <!-- 搜索区 -->
        <div class="flex-1 max-w-2xl">
          <div class="flex">
            <!-- 搜索输入框 -->
            <div class="flex-1 relative">
              <input
                v-model="keyword"
                type="text"
                placeholder="搜索商品、品牌..."
                class="w-full h-10 pl-4 pr-4 text-sm border-2 border-red-600 rounded-l-md focus:outline-none focus:ring-0 bg-white text-gray-700 placeholder-gray-400"
                @keydown="handleKeydown"
              />
            </div>
            <!-- 搜索按钮 -->
            <button
              class="h-10 px-8 bg-red-600 text-white text-sm font-medium rounded-r-md hover:bg-red-700 transition-colors flex items-center gap-2"
              @click="handleSearch"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              搜索
            </button>
          </div>
          <!-- 热门搜索 -->
          <div class="flex items-center gap-3 mt-2">
            <span class="text-xs text-gray-400">热门搜索：</span>
            <button
              v-for="kw in hotKeywords"
              :key="kw"
              class="text-xs text-gray-500 hover:text-red-600 transition-colors"
              @click="handleHotSearch(kw)"
            >
              {{ kw }}
            </button>
          </div>
        </div>

        <!-- 购物车入口 -->
        <div class="flex-shrink-0">
          <button
            class="flex items-center gap-2 h-10 px-5 border border-gray-200 rounded-md hover:border-red-600 hover:text-red-600 transition-colors text-sm text-gray-700 bg-white"
            @click="handleGoCart"
          >
            <!-- 购物车图标 -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <span>购物车</span>
            <!-- 数量角标 -->
            <span
              v-if="cartCount > 0"
              class="flex items-center justify-center min-w-5 h-5 px-1 bg-red-600 text-white text-xs font-medium rounded-full"
            >
              {{ cartCount > 99 ? '99+' : cartCount }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
