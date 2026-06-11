<script setup lang="ts">
/**
 * ============================================
 * 领券中心 (CouponCenterView)
 * 独立营销聚合页：顶部 Banner + 优惠券网格列表
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Coupon {
  id: number
  name: string
  amount: number
  minPoint: number
  type: string
  startTime: string
  endTime: string
  total: number
  received: number
  code: string
}

/** Mock 优惠券数据 */
const coupons = ref<Coupon[]>([
  { id: 1, name: '新客专享券', amount: 200, minPoint: 800, type: '全品类', startTime: '2026-06-01', endTime: '2026-06-30', total: 1000, received: 456, code: 'NEW200' },
  { id: 2, name: '数码品类券', amount: 500, minPoint: 5000, type: '数码电器', startTime: '2026-06-01', endTime: '2026-06-15', total: 500, received: 328, code: 'DIG500' },
  { id: 3, name: '满减优惠券', amount: 100, minPoint: 1000, type: '全品类', startTime: '2026-06-01', endTime: '2026-06-20', total: 2000, received: 1200, code: 'MAN100' },
  { id: 4, name: '生日礼遇券', amount: 300, minPoint: 2000, type: '全品类', startTime: '2026-06-01', endTime: '2026-07-01', total: 300, received: 89, code: 'BDAY300' },
  { id: 5, name: '会员专享券', amount: 150, minPoint: 1500, type: '全品类', startTime: '2026-06-01', endTime: '2026-06-25', total: 800, received: 567, code: 'VIP150' },
  { id: 6, name: '美妆护肤券', amount: 80, minPoint: 600, type: '美妆个护', startTime: '2026-06-01', endTime: '2026-06-18', total: 1500, received: 890, code: 'BEAUTY80' },
  { id: 7, name: '运动户外券', amount: 120, minPoint: 800, type: '运动户外', startTime: '2026-06-01', endTime: '2026-06-22', total: 600, received: 234, code: 'SPORT120' },
  { id: 8, name: '家电大额券', amount: 800, minPoint: 8000, type: '家用电器', startTime: '2026-06-01', endTime: '2026-06-30', total: 200, received: 67, code: 'HOME800' },
  { id: 9, name: '618狂欢券', amount: 618, minPoint: 3000, type: '全品类', startTime: '2026-06-10', endTime: '2026-06-18', total: 1000, received: 0, code: '618GO' },
  { id: 10, name: '首单立减券', amount: 50, minPoint: 200, type: '全品类', startTime: '2026-06-01', endTime: '2026-06-30', total: 5000, received: 3456, code: 'FIRST50' },
])

/** 已领取的券 ID */
const receivedIds = ref<Set<number>>(new Set([1, 3]))

/** 分类筛选 */
const activeCategory = ref('all')
const categories = [
  { key: 'all', label: '全部' },
  { key: '全品类', label: '全品类' },
  { key: '数码电器', label: '数码电器' },
  { key: '家用电器', label: '家用电器' },
  { key: '美妆个护', label: '美妆个护' },
  { key: '运动户外', label: '运动户外' },
]

/** 过滤后的券 */
const filteredCoupons = computed(() => {
  if (activeCategory.value === 'all') return coupons.value
  return coupons.value.filter(c => c.type === activeCategory.value)
})

/** 领取优惠券 */
const receiveCoupon = (id: number) => {
  if (receivedIds.value.has(id)) return
  receivedIds.value.add(id)
}

/** 获取进度百分比 */
const getProgress = (c: Coupon) => Math.round((c.received / c.total) * 100)
</script>

<template>
  <div class="coupon-center-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=300&fit=crop" alt="领券中心" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-red-600/80 to-orange-500/60" />
      <div class="absolute inset-0 flex items-center px-10">
        <div>
          <h1 class="text-3xl font-bold text-white mb-2">领券中心</h1>
          <p class="text-white/80 text-sm">每日更新，大牌好券抢不停</p>
        </div>
        <div class="ml-auto flex items-center gap-6 text-white">
          <div class="text-center">
            <div class="text-2xl font-bold">{{ coupons.length }}</div>
            <div class="text-xs opacity-70">可领券数</div>
          </div>
          <div class="w-px h-10 bg-white/30" />
          <div class="text-center">
            <div class="text-2xl font-bold">{{ receivedIds.size }}</div>
            <div class="text-xs opacity-70">已领取</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 分类筛选 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-5">
      <div class="flex items-center gap-2">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['px-4 py-2 text-sm rounded-lg transition-colors', activeCategory === cat.key ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100']"
          @click="activeCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- ====== 优惠券网格 ====== -->
    <div class="grid grid-cols-2 gap-4">
      <div
        v-for="coupon in filteredCoupons"
        :key="coupon.id"
        class="flex bg-white rounded-xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
      >
        <!-- 左侧金额区 -->
        <div class="w-32 bg-gradient-to-br from-red-600 to-red-500 text-white flex flex-col items-center justify-center flex-shrink-0 py-5 relative">
          <div class="text-3xl font-bold">&yen;{{ coupon.amount }}</div>
          <div class="text-xs opacity-80 mt-1">满{{ coupon.minPoint }}可用</div>
          <!-- 锯齿边缘 -->
          <div class="absolute right-0 top-0 bottom-0 w-2 flex flex-col justify-around">
            <div v-for="i in 8" :key="i" class="w-2 h-2 rounded-full bg-gray-50 -mr-1" />
          </div>
        </div>

        <!-- 右侧信息区 -->
        <div class="flex-1 p-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <h4 class="text-base font-bold text-gray-900">{{ coupon.name }}</h4>
              <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{{ coupon.type }}</span>
            </div>
            <p class="text-xs text-gray-400">有效期：{{ coupon.startTime }} 至 {{ coupon.endTime }}</p>
            <!-- 进度条 -->
            <div class="mt-2 flex items-center gap-2">
              <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-red-500 rounded-full transition-all" :style="{ width: getProgress(coupon) + '%' }" />
              </div>
              <span class="text-xs text-gray-400">{{ getProgress(coupon) }}%</span>
            </div>
            <p class="text-xs text-gray-400 mt-1">已领 {{ coupon.received }}/{{ coupon.total }}</p>
          </div>

          <div class="flex items-center justify-between mt-3">
            <span class="text-xs text-gray-300 font-mono">{{ coupon.code }}</span>
            <button
              :disabled="receivedIds.has(coupon.id) || getProgress(coupon) >= 100"
              :class="[
                'px-5 py-1.5 text-sm rounded-lg font-medium transition-colors',
                receivedIds.has(coupon.id)
                  ? 'bg-gray-100 text-gray-400 cursor-default'
                  : getProgress(coupon) >= 100
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-red-600 text-white hover:bg-red-700',
              ]"
              @click="receiveCoupon(coupon.id)"
            >
              {{ receivedIds.has(coupon.id) ? '已领取' : getProgress(coupon) >= 100 ? '已抢完' : '立即领取' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
