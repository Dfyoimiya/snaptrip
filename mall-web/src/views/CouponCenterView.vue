<script setup lang="ts">
/**
 * ============================================
 * 领券中心 (CouponCenterView)
 * 独立营销聚合页：顶部 Banner + 优惠券网格列表
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAvailableCouponsAPI, addMemberCouponAPI } from '@/apis/coupon'
import type { SmsCoupon } from '@/types/coupon'

const router = useRouter()

/** 加载状态 */
const loading = ref(false)

/** 优惠券列表 */
const coupons = ref<SmsCoupon[]>([])

/** 已领取的券 ID */
const receivedIds = ref<Set<string>>(new Set())
/** 正在领取中的券 ID */
const claimingIds = ref<Set<string>>(new Set())

/** 分类筛选 — useType: 0=全场 1=品类 2=品牌 */
const activeCategory = ref<number | 'all'>('all')
const categories = [
  { key: 'all' as const, label: '全部' },
  { key: 0, label: '全场通用' },
  { key: 1, label: '品类券' },
  { key: 2, label: '品牌券' },
]

/** 过滤后的券 */
const filteredCoupons = computed(() => {
  if (activeCategory.value === 'all') return coupons.value
  return coupons.value.filter(c => c.type === activeCategory.value)
})

/** 领取优惠券 */
const receiveCoupon = async (couponId: string) => {
  if (receivedIds.value.has(couponId) || claimingIds.value.has(couponId)) return
  claimingIds.value.add(couponId)
  try {
    await addMemberCouponAPI(String(couponId))
    receivedIds.value.add(couponId)
  } catch (err: any) {
    console.error('领取失败:', err?.message || err)
  } finally {
    claimingIds.value.delete(couponId)
  }
}

/** 获取进度百分比 */
const getProgress = (c: SmsCoupon) => {
  const total = c.publishCount || c.count || 1
  return Math.round(((c.receiveCount || 0) / total) * 100)
}

/** 加载优惠券列表 */
async function loadCoupons() {
  loading.value = true
  try {
    const res = await getAvailableCouponsAPI(1, 100) as unknown as { items: SmsCoupon[] }
    coupons.value = res.items || []
  } catch (err: any) {
    console.error('加载优惠券失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCoupons()
})
</script>

<template>
  <div class="coupon-center-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=300&fit=crop" alt="领券中心" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-brand-600/80 to-orange-500/60" />
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
          :key="String(cat.key)"
          :class="['px-4 py-2 text-sm rounded-lg transition-colors', activeCategory === cat.key ? 'bg-brand-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100']"
          @click="activeCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- ====== 优惠券网格 ====== -->
    <div v-else class="grid grid-cols-2 gap-4">
      <div
        v-for="coupon in filteredCoupons"
        :key="coupon.id"
        class="flex bg-white rounded-xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
      >
        <!-- 左侧金额区 -->
        <div class="w-32 bg-gradient-to-br from-brand-600 to-brand-500 text-white flex flex-col items-center justify-center flex-shrink-0 py-5 relative">
          <div class="text-3xl font-bold">&yen;{{ coupon.amount }}</div>
          <div class="text-xs opacity-80 mt-1">满{{ coupon.minAmount }}可用</div>
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
              <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{{ ({ 0: '全场通用', 1: '品类券', 2: '品牌券' } as Record<number, string>)[coupon.type] || '通用' }}</span>
            </div>
            <p class="text-xs text-gray-400">有效期：{{ coupon.startTime }} 至 {{ coupon.endTime }}</p>
            <!-- 进度条 -->
            <div class="mt-2 flex items-center gap-2">
              <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-brand-500 rounded-full transition-all" :style="{ width: getProgress(coupon) + '%' }" />
              </div>
              <span class="text-xs text-gray-400">{{ getProgress(coupon) }}%</span>
            </div>
            <p class="text-xs text-gray-400 mt-1">已领 {{ coupon.receiveCount || 0 }}/{{ coupon.publishCount || coupon.count || 0 }}</p>
          </div>

          <div class="flex items-center justify-between mt-3">
            <span class="text-xs text-gray-300 font-mono">{{ coupon.code }}</span>
            <button
              :disabled="receivedIds.has(coupon.id) || getProgress(coupon) >= 100 || claimingIds.has(coupon.id)"
              :class="[
                'px-5 py-1.5 text-sm rounded-lg font-medium transition-colors',
                receivedIds.has(coupon.id)
                  ? 'bg-gray-100 text-gray-400 cursor-default'
                  : getProgress(coupon) >= 100
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-brand-600 text-white hover:bg-brand-700',
              ]"
              @click="receiveCoupon(coupon.id)"
            >
              {{ claimingIds.has(coupon.id) ? '领取中...' : receivedIds.has(coupon.id) ? '已领取' : getProgress(coupon) >= 100 ? '已抢完' : '立即领取' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
