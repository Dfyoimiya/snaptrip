<script setup lang="ts">
/**
 * ============================================
 * 商品搜索列表页 (SearchView)
 * 合并搜索和列表功能
 * 顶部：复杂筛选区（分类、品牌、价格区间、排序）
 * 中部：标准 4 列网格商品卡片
 * 底部：分页器
 * 支持 Keyword + CategoryId + BrandId 组合查询
 * ============================================
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchProductListAPI, getCategoryTreeAPI } from '@/apis/product'
import { getBrandRecommendListAPI } from '@/apis/brand'
import type { PmsProduct, CategoryTreeNode } from '@/types/product'
import type { PmsBrand } from '@/types/brand'

const route = useRoute()
const router = useRouter()

// ===== 筛选状态 =====
const keyword = ref((route.query.keyword as string) || '')
const categoryId = ref<string | undefined>(route.query.categoryId as string | undefined)
const brandId = ref<string | undefined>(route.query.brandId as string | undefined)
const sortType = ref(0)
const minPrice = ref<number | undefined>(undefined)
const maxPrice = ref<number | undefined>(undefined)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)

// ===== 数据 =====
const total = ref(0)
const productList = ref<PmsProduct[]>([])
const categoryOptions = ref<{ id: string; name: string }[]>([])
const brandOptions = ref<{ id: string; name: string }[]>([])

/** 排序选项 */
const sortOptions = [
  { label: '综合排序', value: 0 },
  { label: '销量', value: 2, icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
  { label: '价格从低到高', value: 3 },
  { label: '价格从高到低', value: 4 },
]

/** 价格区间预设 */
const priceRanges = [
  { label: '0-500', min: 0, max: 500 },
  { label: '500-1000', min: 500, max: 1000 },
  { label: '1000-3000', min: 1000, max: 3000 },
  { label: '3000-5000', min: 3000, max: 5000 },
  { label: '5000+', min: 5000, max: undefined },
]

/** 选中价格区间索引 */
const selectedPriceRange = ref(-1)

// ===== 加载筛选选项数据 =====
async function loadFilterOptions() {
  try {
    const [catRes, brandRes] = await Promise.all([
      getCategoryTreeAPI().catch(() => null),
      getBrandRecommendListAPI({ page: 1, page_size: 100 }).catch(() => null),
    ])
    if (catRes) {
      // Flatten category tree to flat list for filter display
      const flat: { id: string; name: string }[] = []
      function walk(nodes: CategoryTreeNode[]) {
        for (const n of nodes) {
          flat.push({ id: n.id, name: n.name })
          if (n.children) walk(n.children)
        }
      }
      walk(Array.isArray(catRes) ? catRes : (catRes as unknown as { data: CategoryTreeNode[] }).data || [])
      categoryOptions.value = flat
    }
    if (brandRes) {
      const brands = Array.isArray(brandRes) ? brandRes : (brandRes as unknown as { data: { items: PmsBrand[] } }).data?.items || []
      brandOptions.value = brands.map(b => ({ id: b.id, name: b.name }))
    }
  } catch {
    // Silently ignore filter loading errors — search still works without filters
  }
}

// ===== 从后端 API 搜索 =====
async function fetchProducts() {
  loading.value = true
  try {
    const res = await searchProductListAPI({
      keyword: keyword.value || undefined,
      productCategoryId: categoryId.value,
      brandId: brandId.value,
      sort: sortType.value,
      minPrice: minPrice.value,
      maxPrice: maxPrice.value,
      pageNum: currentPage.value,
      pageSize,
    }) as unknown as { items: PmsProduct[]; total: number; totalPages: number; page: number }
    productList.value = res.items || []
    total.value = res.total || 0
    totalPages.value = res.totalPages || 1
  } catch (err: any) {
    console.error('搜索失败:', err?.message || err)
    productList.value = []
    total.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

/** 总页数 */
const totalPages = ref(1)

/** 已选筛选标签 */
const activeFilters = computed(() => {
  const filters: { key: string; label: string }[] = []
  if (categoryId.value) {
    const cat = categoryOptions.value.find(c => c.id === categoryId.value)
    if (cat) filters.push({ key: 'category', label: `分类: ${cat.name}` })
  }
  if (brandId.value) {
    const brand = brandOptions.value.find(b => b.id === brandId.value)
    if (brand) filters.push({ key: 'brand', label: `品牌: ${brand.name}` })
  }
  if (minPrice.value !== undefined || maxPrice.value !== undefined) {
    const min = minPrice.value ?? 0
    const max = maxPrice.value ?? '∞'
    filters.push({ key: 'price', label: `价格: ¥${min}-${max}` })
  }
  return filters
})

/** 是否有筛选条件 */
const hasActiveFilters = computed(() => activeFilters.value.length > 0)

// ===== 操作 =====
const selectCategory = (id: string) => {
  categoryId.value = categoryId.value === id ? undefined : id
  currentPage.value = 1
}

const selectBrand = (id: string) => {
  brandId.value = brandId.value === id ? undefined : id
  currentPage.value = 1
}

const selectPriceRange = (index: number) => {
  if (selectedPriceRange.value === index) {
    selectedPriceRange.value = -1
    minPrice.value = undefined
    maxPrice.value = undefined
  } else {
    selectedPriceRange.value = index
    const range = priceRanges[index]
    minPrice.value = range.min
    maxPrice.value = range.max
  }
  currentPage.value = 1
}

const handleSortChange = (sort: number) => {
  sortType.value = sort
  currentPage.value = 1
}

const removeFilter = (key: string) => {
  if (key === 'category') categoryId.value = undefined
  if (key === 'brand') brandId.value = undefined
  if (key === 'price') {
    minPrice.value = undefined
    maxPrice.value = undefined
    selectedPriceRange.value = -1
  }
  currentPage.value = 1
}

const clearAllFilters = () => {
  categoryId.value = undefined
  brandId.value = undefined
  minPrice.value = undefined
  maxPrice.value = undefined
  selectedPriceRange.value = -1
  sortType.value = 0
  currentPage.value = 1
}

const goPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

const goProductDetail = (id: string) => {
  router.push(`/product/${id}`)
}

// 同步 URL 参数变化 + 自动搜索
watch(
  () => [route.query.keyword, route.query.categoryId, route.query.brandId],
  ([kw, cat, brand]) => {
    keyword.value = (kw as string) || ''
    categoryId.value = (cat as string) || undefined
    brandId.value = (brand as string) || undefined
    currentPage.value = 1
    fetchProducts()
  },
  { immediate: true },
)

// 筛选条件变化时重新搜索
watch([categoryId, brandId, sortType, minPrice, maxPrice, currentPage], () => {
  fetchProducts()
})

onMounted(() => {
  loadFilterOptions()
  fetchProducts()
})
</script>

<template>
  <div class="search-page space-y-4">
    <!-- ====== 搜索结果头部 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4">
      <div class="flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">
          <span v-if="keyword">"{{ keyword }}" 的搜索结果</span>
          <span v-else>全部商品</span>
          <span class="text-sm font-normal text-gray-400 ml-2">共 {{ total }} 件商品</span>
        </h1>
        <!-- 排序按钮 -->
        <div class="flex items-center gap-1">
          <button
            v-for="opt in sortOptions"
            :key="opt.value"
            :class="[
              'px-3 py-1.5 text-sm rounded-md transition-colors',
              sortType === opt.value
                ? 'bg-red-600 text-white font-medium'
                : 'text-gray-600 hover:bg-gray-100',
            ]"
            @click="handleSortChange(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- ====== 筛选区 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-100">
      <!-- 分类筛选 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">分类</span>
        <div class="flex flex-wrap gap-2 flex-1">
          <button
            v-for="cat in categoryOptions"
            :key="cat.id"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              categoryId === cat.id
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectCategory(cat.id)"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <!-- 品牌筛选 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">品牌</span>
        <div class="flex flex-wrap gap-2 flex-1">
          <button
            v-for="brand in brandOptions"
            :key="brand.id"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              brandId === brand.id
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectBrand(brand.id)"
          >
            {{ brand.name }}
          </button>
        </div>
      </div>

      <!-- 价格区间 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">价格</span>
        <div class="flex items-center gap-2 flex-1">
          <button
            v-for="(range, index) in priceRanges"
            :key="index"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              selectedPriceRange === index
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectPriceRange(index)"
          >
            ¥{{ range.min }}<template v-if="range.max !== undefined">-{{ range.max }}</template><template v-else>以上</template>
          </button>
          <div class="flex items-center gap-1 ml-2">
            <input
              v-model.number="minPrice"
              type="number"
              placeholder="¥最低"
              class="w-20 h-7 px-2 border border-gray-200 rounded text-sm text-center focus:outline-none focus:border-red-500"
              @blur="currentPage = 1"
            />
            <span class="text-gray-300">-</span>
            <input
              v-model.number="maxPrice"
              type="number"
              placeholder="¥最高"
              class="w-20 h-7 px-2 border border-gray-200 rounded text-sm text-center focus:outline-none focus:border-red-500"
              @blur="currentPage = 1"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 已选筛选标签 ====== -->
    <div v-if="hasActiveFilters" class="flex items-center gap-2">
      <span class="text-sm text-gray-500">已选：</span>
      <span
        v-for="filter in activeFilters"
        :key="filter.key"
        class="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-600 text-xs rounded-full"
      >
        {{ filter.label }}
        <button class="hover:text-red-800" @click="removeFilter(filter.key)">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </span>
      <button class="text-xs text-gray-500 hover:text-red-600 ml-2" @click="clearAllFilters">清除全部</button>
    </div>

    <!-- ====== 商品网格 ====== -->
    <div v-if="productList.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in productList"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="goProductDetail(product.id)"
      >
        <!-- 商品图片 -->
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <!-- 促销标签 -->
          <span
            v-if="(product.originalPrice ?? 0) > product.price"
            class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium"
          >
            省{{ Math.round((1 - product.price / (product.originalPrice || product.price)) * 100) }}%
          </span>
        </div>
        <!-- 商品信息 -->
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ product.price }}</span>
            <span v-if="product.originalPrice" class="text-xs text-gray-400 line-through">&yen;{{ product.originalPrice }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400">已售 {{ (product.saleCount ?? 0) >= 10000 ? ((product.saleCount ?? 0) / 10000).toFixed(1) + '万' : (product.saleCount ?? 0) }}</span>
            <span class="text-xs text-gray-400">{{ product.brandName || '' }}</span>
          </div>
        </div>
      </button>
    </div>

    <!-- ====== 空状态 ====== -->
    <div v-else class="bg-white rounded-xl border border-gray-100 py-20 flex flex-col items-center text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <p class="text-lg">未找到符合条件的商品</p>
      <button class="mt-4 text-sm text-red-600 hover:text-red-700" @click="clearAllFilters">清除筛选条件</button>
    </div>

    <!-- ====== 分页器 ====== -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-4">
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="currentPage === 1"
        @click="goPage(currentPage - 1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <button
        v-for="page in totalPages"
        :key="page"
        :class="[
          'min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors',
          currentPage === page
            ? 'bg-red-600 text-white font-medium'
            : 'border border-gray-200 text-gray-600 hover:bg-gray-50',
        ]"
        @click="goPage(page)"
      >
        {{ page }}
      </button>

      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="currentPage === totalPages"
        @click="goPage(currentPage + 1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <span class="text-sm text-gray-400 ml-3">
        第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 件
      </span>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
