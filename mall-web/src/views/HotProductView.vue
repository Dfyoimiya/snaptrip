<script setup lang="ts">
/**
 * ============================================
 * 热门推荐页 (HotProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 热销排行网格
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
      sort: 2, // sales
      pageNum: 1,
      pageSize: 20,
    }) as unknown as { items: PmsProduct[] }
    products.value = res.items || []
  } catch (err: any) {
    console.error('加载热门商品失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

const formatPrice = (p: number) => p.toLocaleString('zh-CN')

onMounted(() => {
  loadProducts()
})
</script>

<template>
  <div class="hot-product-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=300&fit=crop" alt="热门推荐" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-orange-600/80 to-red-500/60" />
      <div class="absolute inset-0 flex items-center px-10">
        <div>
          <h1 class="text-3xl font-bold text-white mb-2">热门推荐</h1>
          <p class="text-white/80 text-sm">精选好物，品质保障，万人之选</p>
        </div>
        <div class="ml-auto text-white text-center">
          <div class="text-2xl font-bold">{{ products.length }}</div>
          <div class="text-xs opacity-70">款热销</div>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- ====== 热销排行网格 ====== -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="(product, index) in products"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden relative"
        @click="router.push(`/product/${product.id}`)"
      >
        <!-- 排行角标 -->
        <div
          :class="[
            'absolute top-2 left-2 z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white',
            index === 0 ? 'bg-red-600' : index === 1 ? 'bg-orange-500' : index === 2 ? 'bg-yellow-500' : 'bg-gray-400',
          ]"
        >
          {{ index + 1 }}
        </div>

        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.pic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ formatPrice(product.price) }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ formatPrice(product.originalPrice) }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-orange-500 font-medium">已售 {{ product.sale >= 10000 ? (product.sale / 10000).toFixed(1) + '万' : product.sale }}</span>
            <span class="text-xs text-gray-400">{{ product.brandName }}</span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
