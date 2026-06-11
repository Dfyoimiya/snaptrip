<script setup lang="ts">
/**
 * ============================================
 * 个人中心首页 (MemberHomeView)
 * 右侧顶部：用户资产概览
 * 中部：订单状态快捷入口（待付款/待发货等，带角标）
 * 底部：最近订单
 * ============================================
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'

const router = useRouter()
const memberStore = useMemberStore()

/** 用户头像首字母 */
const avatarLetter = computed(() => memberStore.displayName.charAt(0).toUpperCase() || 'U')

/** 订单状态快捷入口 */
const orderStatuses = [
  { label: '待付款', count: 2, icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z', color: 'text-orange-500', bg: 'bg-orange-50' },
  { label: '待发货', count: 1, icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4', color: 'text-blue-500', bg: 'bg-blue-50' },
  { label: '待收货', count: 3, icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z', color: 'text-green-500', bg: 'bg-green-50' },
  { label: '待评价', count: 0, icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z', color: 'text-yellow-500', bg: 'bg-yellow-50' },
  { label: '退款/售后', count: 0, icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15', color: 'text-purple-500', bg: 'bg-purple-50' },
]

/** 功能快捷入口 */
const quickActions = [
  { label: '我的收藏', value: memberStore.memberInfo?.collectProductCount || 15, path: '/member/favorites', color: 'text-red-500' },
  { label: '浏览足迹', value: memberStore.memberInfo?.readCount || 89, path: '/member/favorites', color: 'text-blue-500' },
  { label: '我的优惠券', value: memberStore.memberInfo?.couponCount || 5, path: '/member/coupons', color: 'text-orange-500' },
  { label: '收货地址', value: 3, path: '/member/address', color: 'text-green-500' },
]

/** Mock 最近订单 */
const recentOrders = [
  { id: 'ORD20260608001', status: 0, statusText: '待付款', statusColor: 'text-orange-500 bg-orange-50', totalAmount: 12588, items: [{ name: 'Apple MacBook Air M3 16+512G', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=80&h=80&fit=crop', qty: 1 }, { name: 'Dyson HD15 吹风机', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=80&h=80&fit=crop', qty: 1 }] },
  { id: 'ORD20260607002', status: 2, statusText: '待收货', statusColor: 'text-green-500 bg-green-50', totalAmount: 1540, items: [{ name: 'SK-II 神仙水 230ml', pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=80&h=80&fit=crop', qty: 2 }] },
  { id: 'ORD20260606003', status: 3, statusText: '已完成', statusColor: 'text-gray-500 bg-gray-50', totalAmount: 749, items: [{ name: 'Nike Air Force 1 白色 42码', pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=80&h=80&fit=crop', qty: 1 }] },
]

const formatPrice = (p: number) => p.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
</script>

<template>
  <div class="space-y-5">
    <!-- ====== 用户资产概览卡片 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center gap-5">
        <!-- 头像 -->
        <div class="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 overflow-hidden border-2 border-red-100">
          <img v-if="memberStore.avatar" :src="memberStore.avatar" class="w-full h-full object-cover" />
          <span v-else class="text-2xl font-bold text-red-600">{{ avatarLetter }}</span>
        </div>
        <!-- 信息 -->
        <div class="flex-1">
          <div class="flex items-center gap-3">
            <h2 class="text-xl font-bold text-gray-900">{{ memberStore.displayName }}</h2>
            <span class="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium">黄金会员</span>
          </div>
          <p class="text-sm text-gray-500 mt-1">{{ memberStore.memberInfo?.personalizedSignature || '热爱购物，品质生活' }}</p>
          <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
            <span>手机：{{ memberStore.memberInfo?.phone || '138****8888' }}</span>
            <span>等级：V3</span>
            <span>注册时间：2024-01-15</span>
          </div>
        </div>
        <!-- 资产统计 -->
        <div class="flex items-center gap-6 pl-6 border-l border-gray-100">
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">{{ memberStore.integration }}</div>
            <div class="text-xs text-gray-400 mt-1">积分</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-red-600">{{ memberStore.memberInfo?.couponCount || 0 }}</div>
            <div class="text-xs text-gray-400 mt-1">优惠券</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-orange-500">{{ memberStore.memberInfo?.growth || 3600 }}</div>
            <div class="text-xs text-gray-400 mt-1">成长值</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 订单状态快捷入口 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-bold text-gray-900">我的订单</h3>
        <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/member/orders')">
          查看全部 &rarr;
        </button>
      </div>
      <div class="grid grid-cols-5 gap-4">
        <button
          v-for="status in orderStatuses"
          :key="status.label"
          class="group flex flex-col items-center gap-2 py-4 rounded-lg hover:bg-gray-50 transition-colors relative"
          @click="router.push('/member/orders')"
        >
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', status.bg]">
            <svg xmlns="http://www.w3.org/2000/svg" :class="['h-6 w-6', status.color]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" :d="status.icon" />
            </svg>
          </div>
          <span class="text-sm text-gray-600">{{ status.label }}</span>
          <!-- 角标数字 -->
          <span
            v-if="status.count > 0"
            class="absolute top-2 right-6 min-w-5 h-5 bg-red-600 text-white text-xs rounded-full flex items-center justify-center px-1 font-medium"
          >
            {{ status.count > 99 ? '99+' : status.count }}
          </span>
        </button>
      </div>
    </div>

    <!-- ====== 快捷功能入口 ====== -->
    <div class="grid grid-cols-4 gap-4">
      <button
        v-for="action in quickActions"
        :key="action.label"
        class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4 hover:border-red-200 hover:shadow-md transition-all group"
        @click="router.push(action.path)"
      >
        <div :class="['text-2xl font-bold', action.color]">{{ action.value }}</div>
        <div class="text-sm text-gray-600 group-hover:text-gray-900">{{ action.label }}</div>
      </button>
    </div>

    <!-- ====== 最近订单 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-base font-bold text-gray-900">最近订单</h3>
      </div>
      <div class="divide-y divide-gray-50">
        <div
          v-for="order in recentOrders"
          :key="order.id"
          class="px-6 py-4 hover:bg-gray-50/50 transition-colors"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-3 text-sm">
              <span class="text-gray-500">{{ order.id }}</span>
              <span :class="['text-xs px-2 py-0.5 rounded-full font-medium', order.statusColor]">{{ order.statusText }}</span>
            </div>
            <span class="text-sm font-bold text-gray-900">&yen;{{ formatPrice(order.totalAmount) }}</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="flex -space-x-2">
              <img
                v-for="(item, i) in order.items.slice(0, 3)"
                :key="i"
                :src="item.pic"
                :alt="item.name"
                class="w-10 h-10 rounded-md border-2 border-white object-cover"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-gray-500 truncate">
                {{ order.items.map(i => i.name).join('、') }}
              </p>
            </div>
            <span class="text-xs text-gray-400">共 {{ order.items.reduce((s, i) => s + i.qty, 0) }} 件</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
