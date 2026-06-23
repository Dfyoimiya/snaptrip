<script setup lang="ts">
/**
 * ============================================
 * 个人中心首页 (MemberHomeView)
 * 动态加载：用户资产概览 / 订单状态角标 / 快捷入口计数 / 最近订单
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { getMemberProfileAPI } from '@/apis/member'
import { getOrderListAPI } from '@/apis/order'
import { getMemberCouponListAPI } from '@/apis/coupon'
import { getAddressListAPI } from '@/apis/address'
import { fetchProductCollectionListAPI } from '@/apis/memberProductCollection'
import type { OmsOrderDetail } from '@/types/order'

const router = useRouter()
const memberStore = useMemberStore()

const dashboardLoading = ref(true)
const orderCountByStatus = ref<Record<number, number>>({})
const couponCount = ref(0)
const addressCount = ref(0)
const favoriteCount = ref(0)
const recentOrders = ref<OmsOrderDetail[]>([])
const profileCreatedAt = ref('')

// ── 会员等级计算 ──
const integration = computed(() => memberStore.integration)
const memberLevel = computed(() => {
  const pts = integration.value
  if (pts >= 20000) return { tier: '钻石会员', level: 'V5', next: 0, pct: 100 }
  if (pts >= 5000) return { tier: '黄金会员', level: 'V4', base: 5000, next: 20000, pct: Math.floor(((pts - 5000) / 15000) * 100) }
  if (pts >= 1000) return { tier: '白银会员', level: 'V3', base: 1000, next: 5000, pct: Math.floor(((pts - 1000) / 4000) * 100) }
  return { tier: '普通会员', level: 'V2', base: 0, next: 1000, pct: Math.floor((pts / 1000) * 100) }
})
const growthValue = computed(() => {
  const lv = memberLevel.value
  return lv.next ? lv.next - integration.value : 0
})

const avatarLetter = computed(() => memberStore.displayName.charAt(0).toUpperCase() || 'U')

const formatCreatedAt = (raw: string | null | undefined) => {
  if (!raw) return ''
  const d = new Date(raw)
  if (isNaN(d.getTime())) return raw.slice(0, 10)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// ── 订单状态入口配置 ──
const statusMeta: Record<number, { label: string; icon: string; color: string; bg: string }> = {
  0: { label: '待付款', icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z', color: 'text-orange-500', bg: 'bg-orange-50' },
  1: { label: '待发货', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',        color: 'text-blue-500',   bg: 'bg-blue-50' },
  2: { label: '待收货', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',                         color: 'text-green-500',  bg: 'bg-green-50' },
  3: { label: '待评价', icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z', color: 'text-yellow-500', bg: 'bg-yellow-50' },
  4: { label: '退款/售后', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15', color: 'text-purple-500', bg: 'bg-purple-50' },
}

const orderStatuses = computed(() =>
  [0, 1, 2, 3, 4].map(s => ({
    ...statusMeta[s],
    status: s,
    count: orderCountByStatus.value[s] || 0,
  }))
)

const quickActions = computed(() => [
  { label: '我的收藏',   value: favoriteCount.value, path: '/member/favorites', color: 'text-brand-500' },
  { label: '浏览足迹',   value: 0,                   path: '/member/history',   color: 'text-blue-500' },
  { label: '我的优惠券', value: couponCount.value,   path: '/member/coupons',   color: 'text-orange-500' },
  { label: '收货地址',   value: addressCount.value,  path: '/member/address',   color: 'text-green-500' },
])

// ── 最近订单（取前 4 条） ──
const displayOrders = computed(() => recentOrders.value.slice(0, 4))

const statusTextMap: Record<number, string> = { 0: '待付款', 1: '待发货', 2: '待收货', 3: '已完成', 4: '已取消' }
const statusColorMap: Record<number, string> = {
  0: 'text-orange-500 bg-orange-50', 1: 'text-blue-500 bg-blue-50', 2: 'text-purple-500 bg-purple-50',
  3: 'text-green-500 bg-gray-50', 4: 'text-gray-500 bg-gray-50',
}

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })

onMounted(async () => {
  try {
    // 并行加载所有数据
    const [profile, ordersRes, coupons, addresses, favRes] = await Promise.all([
      getMemberProfileAPI().catch(() => null),
      getOrderListAPI({ page: 1, page_size: 50 }).catch(() => undefined),
      getMemberCouponListAPI(0).catch(() => []),
      getAddressListAPI().catch(() => []),
      fetchProductCollectionListAPI({ pageNum: 1, pageSize: 1 }).catch(() => undefined),
    ])

    // 用户信息
    if (profile) {
      memberStore.setMemberInfo(profile)
      profileCreatedAt.value = formatCreatedAt((profile as any).createdAt ?? (profile as any).created_at)
    }

    // 订单统计
    if (ordersRes) {
      const all = ((ordersRes as any).items || []) as OmsOrderDetail[]
      recentOrders.value = all
      const counts: Record<number, number> = {}
      for (const o of all) {
        counts[o.status] = (counts[o.status] || 0) + 1
      }
      orderCountByStatus.value = counts
    }

    // 计数
    couponCount.value = Array.isArray(coupons) ? coupons.length : 0
    addressCount.value = Array.isArray(addresses) ? addresses.length : 0
    if (favRes) favoriteCount.value = (favRes as any).total || 0
  } catch {
    // silent
  } finally {
    dashboardLoading.value = false
  }
})
</script>

<template>
  <div class="member-home-page">
    <!-- ====== 用户资产概览卡片 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center gap-5">
        <!-- 头像 -->
        <div class="w-20 h-20 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 overflow-hidden border-2 border-red-100">
          <img v-if="memberStore.avatar" :src="memberStore.avatar" class="w-full h-full object-cover" />
          <span v-else class="text-2xl font-bold text-brand-600">{{ avatarLetter }}</span>
        </div>
        <!-- 信息 -->
        <div class="flex-1">
          <div class="flex items-center gap-3">
            <h2 class="text-xl font-bold text-gray-900">{{ memberStore.displayName }}</h2>
            <span class="text-xs bg-brand-100 text-brand-600 px-2 py-0.5 rounded-full font-medium">{{ memberLevel.tier }}</span>
          </div>
          <p class="text-sm text-gray-500 mt-1">积分 {{ integration }} · 距下一级还需 {{ growthValue }} 积分</p>
          <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
            <span>{{ memberStore.memberInfo?.email || '' }}</span>
            <span>等级：{{ memberLevel.level }}</span>
            <span v-if="profileCreatedAt">注册时间：{{ profileCreatedAt }}</span>
          </div>
        </div>
        <!-- 资产统计 -->
        <div class="flex items-center gap-6 pl-6 border-l border-gray-100">
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">{{ memberStore.integration }}</div>
            <div class="text-xs text-gray-400 mt-1">积分</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-brand-600">{{ couponCount }}</div>
            <div class="text-xs text-gray-400 mt-1">优惠券</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-orange-500">{{ growthValue }}</div>
            <div class="text-xs text-gray-400 mt-1">距下一级</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 订单状态快捷入口 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-bold text-gray-900">我的订单</h3>
        <button class="text-sm text-gray-500 hover:text-brand-600 transition-colors" @click="router.push('/member/orders')">
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
            class="absolute top-2 right-6 min-w-5 h-5 bg-brand-600 text-white text-xs rounded-full flex items-center justify-center px-1 font-medium"
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
        class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4 hover:border-brand-200 hover:shadow-md transition-all group"
        @click="router.push(action.path)"
      >
        <div :class="['text-2xl font-bold', action.color]">{{ action.value }}</div>
        <div class="text-sm text-gray-600 group-hover:text-gray-900">{{ action.label }}</div>
      </button>
    </div>

    <!-- ====== 最近订单 ====== -->
    <div class="recent-orders-card bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-base font-bold text-gray-900">最近订单</h3>
      </div>
      <div v-if="dashboardLoading" class="recent-orders-body flex justify-center text-gray-400">加载中...</div>

      <div v-else class="recent-orders-body divide-y divide-gray-50">
        <div
          v-for="order in displayOrders"
          :key="order.id"
          class="px-6 py-4 hover:bg-gray-50/50 transition-colors cursor-pointer"
          @click="router.push(`/order/${order.id}`)"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-3 text-sm">
              <span class="text-gray-500 font-mono">{{ order.orderSn }}</span>
              <span :class="['text-xs px-2 py-0.5 rounded-full font-medium', statusColorMap[order.status] || 'text-gray-500 bg-gray-50']">{{ statusTextMap[order.status] || '未知' }}</span>
            </div>
            <span class="text-sm font-bold text-gray-900">&yen;{{ formatPrice(order.payAmount) }}</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="flex -space-x-2">
              <img
                v-for="(item, i) in order.items.slice(0, 3)"
                :key="i"
                :src="item.productPic"
                :alt="item.productName"
                class="w-10 h-10 rounded-md border-2 border-white object-cover"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-gray-500 truncate">
                {{ order.items.map(i => i.productName).join('、') }}
              </p>
            </div>
            <span class="text-xs text-gray-400">共 {{ order.items.reduce((s, i) => s + i.quantity, 0) }} 件</span>
          </div>
        </div>

        <div v-if="displayOrders.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400">
          <p class="text-sm">暂无订单</p>
          <button class="mt-3 text-sm text-brand-600 hover:text-brand-700" @click="router.push('/')">去逛逛</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.member-home-page {
  display: flex;
  min-height: calc(100vh - 128px);
  flex-direction: column;
  gap: 20px;
}

.recent-orders-card {
  display: flex;
  flex: 1;
  min-height: 300px;
  flex-direction: column;
}

.recent-orders-body {
  flex: 1;
}
</style>
