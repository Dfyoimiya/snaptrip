<script setup lang="ts">
/**
 * ============================================
 * 我的优惠券页 (MemberCouponsView)
 * 个人中心侧边栏子路由
 * ============================================
 */
import { ref } from 'vue'

const activeTab = ref<'valid' | 'used' | 'expired'>('valid')

const validCoupons = ref([
  { id: 1, name: '新客专享券', amount: 200, minPoint: 800, endTime: '2026-06-30', code: 'NEW200', type: '全品类' },
  { id: 2, name: '数码品类券', amount: 500, minPoint: 5000, endTime: '2026-06-15', code: 'DIG500', type: '数码电器' },
  { id: 3, name: '满减优惠券', amount: 100, minPoint: 1000, endTime: '2026-06-20', code: 'MAN100', type: '全品类' },
  { id: 4, name: '生日礼遇券', amount: 300, minPoint: 2000, endTime: '2026-07-01', code: 'BDAY300', type: '全品类' },
  { id: 5, name: '会员专享券', amount: 150, minPoint: 1500, endTime: '2026-06-25', code: 'VIP150', type: '全品类' },
])

const usedCoupons = ref([
  { id: 6, name: '618预热券', amount: 100, minPoint: 500, usedTime: '2026-06-01', code: '618100' },
  { id: 7, name: '品牌联合券', amount: 200, minPoint: 2000, usedTime: '2026-05-28', code: 'BRAND200' },
])

const expiredCoupons = ref([
  { id: 8, name: '五一特惠券', amount: 100, minPoint: 800, endTime: '2026-05-05', code: 'LABOR100' },
])
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <div class="px-6 py-4 border-b border-gray-100">
      <h2 class="text-lg font-bold text-gray-900">我的优惠券</h2>
    </div>

    <!-- Tab 筛选 -->
    <div class="px-6 py-3 border-b border-gray-100 flex items-center gap-2">
      <button
        v-for="tab in [{k:'valid',l:'可使用'}, {k:'used',l:'已使用'}, {k:'expired',l:'已过期'}]"
        :key="tab.k"
        :class="[
          'px-4 py-2 text-sm rounded-lg transition-colors',
          activeTab === tab.k ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100',
        ]"
        @click="activeTab = tab.k as 'valid' | 'used' | 'expired'"
      >
        {{ tab.l }} ({{ tab.k === 'valid' ? validCoupons.length : tab.k === 'used' ? usedCoupons.length : expiredCoupons.length }})
      </button>
    </div>

    <!-- 可使用 -->
    <div v-if="activeTab === 'valid'" class="p-5 grid grid-cols-2 gap-4">
      <div
        v-for="coupon in validCoupons"
        :key="coupon.id"
        class="flex border border-red-100 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="w-28 bg-red-600 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
          <div class="text-2xl font-bold">&yen;{{ coupon.amount }}</div>
          <div class="text-xs opacity-80 mt-1">满{{ coupon.minPoint }}可用</div>
        </div>
        <div class="flex-1 p-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2">
              <h4 class="text-sm font-bold text-gray-900">{{ coupon.name }}</h4>
              <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{{ coupon.type }}</span>
            </div>
            <p class="text-xs text-gray-400 mt-1">有效期至 {{ coupon.endTime }}</p>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400 font-mono">{{ coupon.code }}</span>
            <button class="text-xs bg-red-600 text-white px-3 py-1.5 rounded hover:bg-red-700 transition-colors">去使用</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 已使用 -->
    <div v-if="activeTab === 'used'" class="p-5 grid grid-cols-2 gap-4">
      <div
        v-for="coupon in usedCoupons"
        :key="coupon.id"
        class="flex border border-gray-200 rounded-lg overflow-hidden opacity-60"
      >
        <div class="w-28 bg-gray-400 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
          <div class="text-2xl font-bold">&yen;{{ coupon.amount }}</div>
          <div class="text-xs opacity-80 mt-1">满{{ coupon.minPoint }}可用</div>
        </div>
        <div class="flex-1 p-4 flex flex-col justify-between">
          <div>
            <h4 class="text-sm font-bold text-gray-500">{{ coupon.name }}</h4>
            <p class="text-xs text-gray-400 mt-1">使用时间 {{ coupon.usedTime }}</p>
          </div>
          <div class="mt-2">
            <span class="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded">已使用</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 已过期 -->
    <div v-if="activeTab === 'expired'" class="p-5 grid grid-cols-2 gap-4">
      <div
        v-for="coupon in expiredCoupons"
        :key="coupon.id"
        class="flex border border-gray-200 rounded-lg overflow-hidden opacity-50"
      >
        <div class="w-28 bg-gray-400 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
          <div class="text-2xl font-bold">&yen;{{ coupon.amount }}</div>
          <div class="text-xs opacity-80 mt-1">满{{ coupon.minPoint }}可用</div>
        </div>
        <div class="flex-1 p-4 flex flex-col justify-between">
          <div>
            <h4 class="text-sm font-bold text-gray-500">{{ coupon.name }}</h4>
            <p class="text-xs text-gray-400 mt-1">已于 {{ coupon.endTime }} 过期</p>
          </div>
          <div class="mt-2">
            <span class="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded">已过期</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
