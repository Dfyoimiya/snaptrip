<script setup lang="ts">
/**
 * ============================================
 * 品牌详情页 (BrandDetailView)
 * ============================================
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ProductCard from '@/components/product/ProductCard.vue'
import { getBrandDetailAPI, getBrandProductListAPI } from '@/apis/brand'

const route = useRoute()
const router = useRouter()

interface BrandInfo {
  id: string
  name: string
  logo?: string
  bigPic?: string
  brandStory?: string
}

interface ProductItem {
  id: string
  name: string
  defaultPic?: string | null
  price: number
  originalPrice?: number | null
  saleCount?: number
  subTitle?: string | null
}

const brand = ref<BrandInfo | null>(null)
const products = ref<ProductItem[]>([])
const total = ref(0)
const loading = ref(false)
const sortType = ref(0)
const currentPage = ref(1)
const pageSize = 12

const sortOptions = [
  { label: '综合排序', value: 0 },
  { label: '销量', value: 2 },
  { label: '价格从低到高', value: 3 },
  { label: '价格从高到低', value: 4 },
  { label: '新品', value: 1 },
]

const totalPages = ref(1)

async function loadData() {
  const brandId = route.params.id as string
  if (!brandId) return
  loading.value = true
  try {
    const [brandData, productData] = await Promise.all([
      getBrandDetailAPI(brandId),
      getBrandProductListAPI(brandId, currentPage.value, pageSize, sortType.value),
    ])
    brand.value = brandData as unknown as BrandInfo
    const pd = productData as any
    products.value = (pd?.items || pd?.list || []) as ProductItem[]
    total.value = pd?.total || 0
    totalPages.value = pd?.totalPages || Math.ceil(total.value / pageSize)
  } catch {
    brand.value = null
  } finally {
    loading.value = false
  }
}

const formatPrice = (p: number) => p?.toLocaleString?.('zh-CN') || String(p)

function goProductDetail(id: string) {
  router.push(`/product/${id}`)
}

onMounted(loadData)
watch(() => route.params.id, loadData)
watch(currentPage, () => loadData())
watch(sortType, () => { currentPage.value = 1; loadData() })
</script>

<template>
  <div class="brand-detail-page space-y-5">
    <!-- 品牌 Banner -->
    <div v-if="brand" class="relative rounded-xl overflow-hidden h-[200px] bg-gradient-to-r from-gray-800 to-gray-600">
      <img v-if="brand.bigPic" :src="brand.bigPic" :alt="brand.name" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent" />
      <div class="absolute inset-0 flex items-center px-8">
        <div class="flex items-center gap-5">
          <div class="w-20 h-20 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center overflow-hidden">
            <img v-if="brand.logo" :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover" />
            <span v-else class="text-white text-2xl font-bold">{{ brand.name?.charAt(0) }}</span>
          </div>
          <div>
            <h1 class="text-2xl font-bold text-white">{{ brand.name }}</h1>
            <p v-if="brand.brandStory" class="text-sm text-white/70 mt-1 max-w-lg">{{ brand.brandStory }}</p>
            <p class="text-xs text-white/50 mt-2">{{ total }} 件商品在售</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 排序 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1">
          <button
            v-for="opt in sortOptions"
            :key="opt.value"
            :class="['px-4 py-2 text-sm rounded-md transition-colors', sortType === opt.value ? 'bg-brand-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100']"
            @click="sortType = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
        <span class="text-sm text-gray-400">共 {{ total }} 件商品</span>
      </div>
    </div>

    <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      加载中...
    </div>

    <!-- 商品网格 -->
    <div v-else-if="products.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
        :show-discount-badge="(product.originalPrice ?? 0) > product.price"
        @click="goProductDetail(product.id)"
      />
    </div>

    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      暂无商品
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-4">
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >&lt;</button>
      <button
        v-for="page in totalPages"
        :key="page"
        :class="['min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors', currentPage === page ? 'bg-brand-600 text-white font-medium' : 'border border-gray-200 text-gray-600 hover:bg-gray-50']"
        @click="currentPage = page"
      >{{ page }}</button>
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
        :disabled="currentPage === totalPages"
        @click="currentPage++"
      >&gt;</button>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
