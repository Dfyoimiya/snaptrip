<script setup lang="ts">
/**
 * ============================================
 * 共享产品卡片组件 (ProductCard)
 * Taobao 无框风格：图片 + 下方文字，无边框无阴影
 * ============================================
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { PmsProduct } from '@/types/product'

const props = withDefaults(
  defineProps<{
    product: PmsProduct
    rank?: number
    showRank?: boolean
    showNewBadge?: boolean
    showDiscountBadge?: boolean
  }>(),
  {
    rank: undefined,
    showRank: false,
    showNewBadge: false,
    showDiscountBadge: false,
  },
)

const router = useRouter()

const productImage = computed(() => props.product.defaultPic || '')
const discountPercent = computed(() => {
  if (!props.product.originalPrice || props.product.originalPrice <= props.product.price) return 0
  return Math.round((1 - props.product.price / props.product.originalPrice) * 100)
})
const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN')
const formatSaleCount = (count: number | null | undefined) => {
  const n = count ?? 0
  return n >= 10000 ? (n / 10000).toFixed(1) + '万' : String(n)
}

const rankBgClass = computed(() => {
  if (props.rank === 0) return 'bg-brand-600'
  if (props.rank === 1) return 'bg-orange-500'
  if (props.rank === 2) return 'bg-yellow-500'
  return 'bg-gray-400'
})

function goDetail(id: string) {
  if (!id || id === 'undefined') return
  router.push(`/product/${id}`)
}
</script>

<template>
  <button
    class="group text-left block w-full"
    @click="goDetail(product.id)"
  >
    <!-- 商品图片 -->
    <div class="aspect-square bg-gray-50 rounded-xl overflow-hidden relative">
      <img
        :src="productImage"
        :alt="product.name"
        class="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
      />

      <!-- 排行角标 -->
      <div
        v-if="showRank && rank !== undefined"
        :class="[
          'absolute top-2 left-2 z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white',
          rankBgClass,
        ]"
      >
        {{ rank + 1 }}
      </div>

      <!-- NEW 角标 -->
      <span
        v-if="showNewBadge"
        class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded-full font-medium"
      >NEW</span>

      <!-- 折扣角标 -->
      <span
        v-if="showDiscountBadge && discountPercent > 0"
        class="absolute top-2 right-2 bg-brand-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium"
      >
        省{{ discountPercent }}%
      </span>
    </div>

    <!-- 商品信息 (无框) -->
    <div class="pt-2">
      <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-1 group-hover:text-brand-600 transition-colors">
        {{ product.name }}
      </p>
      <div class="flex items-baseline gap-2">
        <span class="text-brand-600 font-bold text-base">
          <span class="text-xs">&yen;</span>{{ formatPrice(product.promotionPrice ?? product.price) }}
        </span>
        <span
          v-if="product.originalPrice && product.originalPrice > (product.promotionPrice ?? product.price)"
          class="text-xs text-gray-400 line-through"
        >&yen;{{ formatPrice(product.originalPrice) }}</span>
      </div>
      <div class="flex items-center justify-between mt-1">
        <span class="text-xs text-gray-400">已售 {{ formatSaleCount(product.saleCount) }}</span>
        <span v-if="product.brandName" class="text-xs text-gray-400">{{ product.brandName }}</span>
      </div>
    </div>
  </button>
</template>
