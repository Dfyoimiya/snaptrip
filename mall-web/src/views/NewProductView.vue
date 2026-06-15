<script setup lang="ts">
/**
 * ============================================
 * 新品首发页 (NewProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 新品商品网格
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { searchProductListAPI } from '@/apis/product'
import type { PmsProduct } from '@/types/product'

const router = useRouter()

const loading = ref(false)
const products = ref<PmsProduct[]>([])

async function loadProducts() {
  loading.value = true
  try {
    const res = await searchProductListAPI({
      sort: 1, // new
      pageNum: 1,
      pageSize: 20,
    }) as unknown as { items: PmsProduct[] }
    products.value = res.items || []
  } catch (err: any) {
    console.error('加载新品失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN')

onMounted(() => {
  loadProducts()
})
</script>

<template>
  <div class="new-product-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=1200&h=300&fit=crop" alt="新品首发" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-green-600/80 to-emerald-500/60" />
      <div class="absolute inset-0 flex items-center px-10">
        <div>
          <h1 class="text-3xl font-bold text-white mb-2">新品首发</h1>
          <p class="text-white/80 text-sm">新鲜好物，抢先体验</p>
        </div>
        <div class="ml-auto text-white text-center">
          <div class="text-2xl font-bold">{{ products.length }}</div>
          <div class="text-xs opacity-70">款新品</div>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- ====== 新品商品网格 ====== -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in products"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="router.push(`/product/${product.id}`)"
      >
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <span class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded-full font-medium">NEW</span>
          <span v-if="product.originalPrice > product.price" class="absolute top-2 right-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
            省{{ Math.round((1 - product.price / product.originalPrice) * 100) }}%
          </span>
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-green-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ formatPrice(product.price) }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ formatPrice(product.originalPrice) }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400">已售 {{ (product.saleCount ?? 0) >= 10000 ? ((product.saleCount ?? 0) / 10000).toFixed(1) + '万' : (product.saleCount ?? 0) }}</span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
