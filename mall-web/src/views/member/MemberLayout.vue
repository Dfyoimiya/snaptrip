<script setup lang="ts">
/**
 * ============================================
 * 会员中心布局组件 (MemberLayout)
 * 标准 PC 端：左侧通用侧边栏导航 + 右侧内容面板
 * ============================================
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'

const route = useRoute()
const router = useRouter()
const memberStore = useMemberStore()

/** 侧边栏菜单 */
const sidebarMenus = [
  {
    label: '个人中心',
    path: '/member',
    icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  },
  {
    label: '我的订单',
    path: '/member/orders',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  },
  {
    label: '我的收藏',
    path: '/member/favorites',
    icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
  },
  {
    label: '收货地址',
    path: '/member/address',
    icon: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z',
  },
  {
    label: '我的优惠券',
    path: '/member/coupons',
    icon: 'M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z',
  },
  {
    label: '浏览足迹',
    path: '/member/history',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    label: '品牌关注',
    path: '/member/brands',
    icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
  },
  {
    label: '账号设置',
    path: '/member/settings',
    icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  },
]

/** 判断菜单是否激活 */
const isMenuActive = (path: string) => {
  return route.path === path
}

/** 用户头像首字母 */
const avatarLetter = computed(() => {
  return memberStore.displayName.charAt(0).toUpperCase() || 'U'
})
</script>

<template>
  <div class="flex gap-5 min-h-[600px]">
    <!-- ====== 左侧侧边栏 ====== -->
    <aside class="w-[220px] flex-shrink-0">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden sticky top-4">
        <!-- 用户信息摘要 -->
        <div class="p-5 border-b border-gray-100 bg-gradient-to-br from-red-50 to-white">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
              <img v-if="memberStore.avatar" :src="memberStore.avatar" class="w-full h-full object-cover" />
              <span v-else class="text-lg font-bold text-red-600">{{ avatarLetter }}</span>
            </div>
            <div class="min-w-0">
              <p class="text-sm font-bold text-gray-900 truncate">{{ memberStore.displayName }}</p>
              <p class="text-xs text-gray-400 mt-0.5">{{ memberStore.memberInfo?.phone || '138****8888' }}</p>
            </div>
          </div>
          <!-- 积分资产 -->
          <div class="flex items-center justify-between mt-4 pt-3 border-t border-red-100/60">
            <div class="text-center flex-1">
              <div class="text-sm font-bold text-red-600">{{ memberStore.integration }}</div>
              <div class="text-[10px] text-gray-400">积分</div>
            </div>
            <div class="w-px h-6 bg-red-100" />
            <div class="text-center flex-1">
              <div class="text-sm font-bold text-orange-500">{{ memberStore.memberInfo?.couponCount || 0 }}</div>
              <div class="text-[10px] text-gray-400">优惠券</div>
            </div>
            <div class="w-px h-6 bg-red-100" />
            <div class="text-center flex-1">
              <div class="text-sm font-bold text-gray-700">V3</div>
              <div class="text-[10px] text-gray-400">等级</div>
            </div>
          </div>
        </div>

        <!-- 菜单列表 -->
        <nav class="py-2">
          <button
            v-for="menu in sidebarMenus"
            :key="menu.path"
            :class="[
              'w-full flex items-center gap-3 px-5 py-3 text-sm transition-colors text-left',
              isMenuActive(menu.path)
                ? 'text-red-600 bg-red-50 font-medium border-l-3 border-red-600'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
            ]"
            @click="router.push(menu.path)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" :d="menu.icon" />
            </svg>
            <span>{{ menu.label }}</span>
          </button>
        </nav>
      </div>
    </aside>

    <!-- ====== 右侧内容面板 ====== -->
    <main class="flex-1 min-w-0">
      <RouterView />
    </main>
  </div>
</template>
