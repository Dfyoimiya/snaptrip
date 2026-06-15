<script setup lang="ts">
/**
 * ============================================
 * 我的优惠券页 (MemberCouponsView)
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { getMemberCouponListAPI } from '@/apis/coupon'

interface CouponItem {
  id: string
  couponName?: string
  couponAmount?: number
  couponMinAmount?: number
  expireTime?: string
  useStatus?: number
  useTime?: string
}

const activeTab = ref<'valid' | 'used' | 'expired'>('valid')
const validCoupons = ref<CouponItem[]>([])
const usedCoupons = ref<CouponItem[]>([])
const expiredCoupons = ref<CouponItem[]>([])
const loading = ref(false)

async function loadCoupons() {
  loading.value = true
  try {
    const [valid, used, expired] = await Promise.all([
      getMemberCouponListAPI(0).catch(() => [] as CouponItem[]),
      getMemberCouponListAPI(1).catch(() => [] as CouponItem[]),
      getMemberCouponListAPI(2).catch(() => [] as CouponItem[]),
    ])
    validCoupons.value = (valid as CouponItem[]) || []
    usedCoupons.value = (used as CouponItem[]) || []
    expiredCoupons.value = (expired as CouponItem[]) || []
  } catch {
    // keep empty
  } finally {
    loading.value = false
  }
}

onMounted(loadCoupons)
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

    <div v-if="loading" class="flex items-center justify-center py-20">
      <p class="text-gray-400">加载中...</p>
    </div>

    <!-- 可使用 -->
    <div v-else-if="activeTab === 'valid'" class="p-5">
      <div v-if="validCoupons.length" class="grid grid-cols-2 gap-4">
        <div
          v-for="coupon in validCoupons"
          :key="coupon.id"
          class="flex border border-red-100 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
        >
          <div class="w-28 bg-red-600 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
            <div class="text-2xl font-bold">&yen;{{ coupon.couponAmount }}</div>
            <div class="text-xs opacity-80 mt-1">满{{ coupon.couponMinAmount }}可用</div>
          </div>
          <div class="flex-1 p-4 flex flex-col justify-between">
            <div>
              <h4 class="text-sm font-bold text-gray-900">{{ coupon.couponName }}</h4>
              <p v-if="coupon.expireTime" class="text-xs text-gray-400 mt-1">有效期至 {{ coupon.expireTime }}</p>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
        <p>暂无可用优惠券</p>
      </div>
    </div>

    <!-- 已使用 -->
    <div v-else-if="activeTab === 'used'" class="p-5">
      <div v-if="usedCoupons.length" class="grid grid-cols-2 gap-4">
        <div
          v-for="coupon in usedCoupons"
          :key="coupon.id"
          class="flex border border-gray-200 rounded-lg overflow-hidden opacity-60"
        >
          <div class="w-28 bg-gray-400 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
            <div class="text-2xl font-bold">&yen;{{ coupon.couponAmount }}</div>
            <div class="text-xs opacity-80 mt-1">满{{ coupon.couponMinAmount }}可用</div>
          </div>
          <div class="flex-1 p-4 flex flex-col justify-between">
            <div>
              <h4 class="text-sm font-bold text-gray-500">{{ coupon.couponName }}</h4>
              <p v-if="coupon.useTime" class="text-xs text-gray-400 mt-1">使用时间 {{ coupon.useTime }}</p>
            </div>
            <div class="mt-2">
              <span class="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded">已使用</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
        <p>暂无已使用优惠券</p>
      </div>
    </div>

    <!-- 已过期 -->
    <div v-else class="p-5">
      <div v-if="expiredCoupons.length" class="grid grid-cols-2 gap-4">
        <div
          v-for="coupon in expiredCoupons"
          :key="coupon.id"
          class="flex border border-gray-200 rounded-lg overflow-hidden opacity-50"
        >
          <div class="w-28 bg-gray-400 text-white flex flex-col items-center justify-center flex-shrink-0 py-4">
            <div class="text-2xl font-bold">&yen;{{ coupon.couponAmount }}</div>
            <div class="text-xs opacity-80 mt-1">满{{ coupon.couponMinAmount }}可用</div>
          </div>
          <div class="flex-1 p-4 flex flex-col justify-between">
            <div>
              <h4 class="text-sm font-bold text-gray-500">{{ coupon.couponName }}</h4>
              <p v-if="coupon.expireTime" class="text-xs text-gray-400 mt-1">已于 {{ coupon.expireTime }} 过期</p>
            </div>
            <div class="mt-2">
              <span class="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded">已过期</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
        <p>暂无过期优惠券</p>
      </div>
    </div>
  </div>
</template>
