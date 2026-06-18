<script setup lang="ts">
/**
 * ============================================
 * 新品首发页 (NewProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 新品商品网格
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ProductCard from '@/components/product/ProductCard.vue'
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
      page: 1,
      pageSize: 20,
    })
    products.value = res.items || []
  } catch (err: any) {
    console.error('加载新品失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

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
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
        :show-new-badge="true"
        :show-discount-badge="(product.originalPrice ?? 0) > product.price"
        @click="router.push(`/product/${product.id}`)"
      />
    </div>
  </div>
</template>
