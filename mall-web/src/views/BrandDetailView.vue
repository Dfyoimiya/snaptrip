<script setup lang="ts">
/**
 * ============================================
 * 品牌详情页 (BrandDetailView)
 * ============================================
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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

const totalPages = computed(() => Math.ceil(total.value / pageSize))

const paginatedProducts = computed(() => {
  let result = [...products.value]
  if (sortType.value === 2) result.sort((a, b) => (b.saleCount || 0) - (a.saleCount || 0))
  else if (sortType.value === 3) result.sort((a, b) => a.price - b.price)
  else if (sortType.value === 4) result.sort((a, b) => b.price - a.price)
  return result
})

async function loadData() {
  const brandId = route.params.id as string
  if (!brandId) return
  loading.value = true
  try {
    const [brandData, productData] = await Promise.all([
      getBrandDetailAPI(brandId),
      getBrandProductListAPI(brandId, currentPage.value, pageSize),
    ])
    brand.value = brandData as unknown as BrandInfo
    const pd = productData as any
    products.value = (pd?.items || pd?.list || []) as ProductItem[]
    total.value = pd?.total || products.value.length
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
            :class="['px-4 py-2 text-sm rounded-md transition-colors', sortType === opt.value ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100']"
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
    <div v-else-if="paginatedProducts.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in paginatedProducts"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="goProductDetail(product.id)"
      >
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img v-if="product.defaultPic" :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <div v-else class="w-full h-full flex items-center justify-center text-gray-300">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          </div>
          <span v-if="product.originalPrice && product.originalPrice > product.price" class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
            省{{ Math.round((1 - product.price / product.originalPrice) * 100) }}%
          </span>
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ product.price }}</span>
            <span v-if="product.originalPrice && product.originalPrice > product.price" class="text-xs text-gray-400 line-through">&yen;{{ product.originalPrice }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span v-if="product.saleCount" class="text-xs text-gray-400">已售 {{ (product.saleCount ?? 0) >= 10000 ? ((product.saleCount ?? 0) / 10000).toFixed(1) + '万' : (product.saleCount ?? 0) }}</span>
            <span v-if="product.subTitle" class="text-xs text-gray-400">{{ product.subTitle }}</span>
          </div>
        </div>
      </button>
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
        :class="['min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors', currentPage === page ? 'bg-red-600 text-white font-medium' : 'border border-gray-200 text-gray-600 hover:bg-gray-50']"
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
