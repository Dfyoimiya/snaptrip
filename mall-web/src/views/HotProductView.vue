<script setup lang="ts">
/**
 * ============================================
 * 热门推荐页 (HotProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 热销排行网格
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ProductCard from '@/components/product/ProductCard.vue'
import { searchProductListAPI } from '@/apis/product'
import type { PmsProduct } from '@/types/product'

const router = useRouter()

const loading = ref(false)
const products = ref<PmsProduct[]>([])
const currentPage = ref(1)
const total = ref(0)
const pageSize = 20

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function loadProducts() {
  loading.value = true
  try {
    const res = await searchProductListAPI({
      sort: 2, // sales
      page: currentPage.value,
      pageSize,
    })
    products.value = res.items || []
    total.value = res.total || 0
  } catch (err: any) {
    console.error('加载热门商品失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

const goPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadProducts()
}

onMounted(() => {
  loadProducts()
})
</script>

<template>
  <div class="hot-product-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=300&fit=crop" alt="热门推荐" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-orange-600/80 to-brand-500/60" />
      <div class="absolute inset-0 flex items-center px-10">
        <div>
          <h1 class="text-3xl font-bold text-white mb-2">热门推荐</h1>
          <p class="text-white/80 text-sm">精选好物，品质保障，万人之选</p>
        </div>
        <div class="ml-auto text-white text-center">
          <div class="text-2xl font-bold">{{ total }}</div>
          <div class="text-xs opacity-70">款热销</div>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- ====== 热销排行网格 ====== -->
    <div v-else-if="products.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <ProductCard
        v-for="(product, index) in products"
        :key="product.id"
        :product="product"
        :rank="index"
        :show-rank="true"
        @click="router.push(`/product/${product.id}`)"
      />
    </div>

    <!-- 空状态 -->
    <div v-else class="flex justify-center py-20 text-gray-400">暂无热门商品</div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-4">
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
        :disabled="currentPage === 1"
        @click="goPage(currentPage - 1)"
      >&lt;</button>
      <button
        v-for="page in totalPages"
        :key="page"
        :class="['min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors', currentPage === page ? 'bg-brand-600 text-white font-medium' : 'border border-gray-200 text-gray-600 hover:bg-gray-50']"
        @click="goPage(page)"
      >{{ page }}</button>
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
        :disabled="currentPage === totalPages"
        @click="goPage(currentPage + 1)"
      >&gt;</button>
      <span class="text-sm text-gray-400 ml-3">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 件</span>
    </div>
  </div>
</template>
