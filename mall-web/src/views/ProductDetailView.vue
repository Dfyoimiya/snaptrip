<script setup lang="ts">
/**
 * ============================================
 * 商品详情页 (ProductDetailView) — 淘宝式布局
 * 左列：主图+放大镜+缩略图（随页面滚动）
 * 右列：sticky 面板（独立滚动）— 名称 → 价格 → SKU 色块 → 数量 → 领券购买/收藏
 * 下方：详情 Tab
 * ============================================
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { addCartAPI } from '@/apis/cart'
import { getProductDetailAPI } from '@/apis/product'
import { createProductCollectionAPI, deleteProductCollectionAPI, fetchProductCollectionListAPI } from '@/apis/memberProductCollection'
import { trackView } from '@/utils/tracker'
import { listReviewsAPI, type ReviewItem } from '@/apis/review'
import ReviewForm from '@/components/product/ReviewForm.vue'
import { useCartStore } from '@/stores/cart'
import { useMemberStore } from '@/stores/member'
import DOMPurify from 'dompurify'
import type { PmsSkuStock } from '@/types/product'
import type { PmsBrand } from '@/types/brand'
import type { SmsCoupon } from '@/types/coupon'

// ── DOMPurify 配置：给 <img> 加 onerror 兜底 & lazy loading ──
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'IMG') {
    // 图片加载失败时显示占位背景
    node.setAttribute('loading', 'lazy')
    node.setAttribute('onerror', "this.style.display='block';this.style.background='#f3f4f6';this.style.minWidth='80px';this.style.minHeight='80px';this.style.borderRadius='8px';this.alt='图片加载失败'")
  }
})

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const memberStore = useMemberStore()

// ============================================================
// 商品详情（从后端 API 加载）
// ============================================================

interface MockProductDetail {
  product: {
    id: number | string
    name: string
    subTitle: string
    price: number
    originalPrice: number
    sale: number
    stock: number
    brandName: string
    productCategoryName: string
    pic: string
    albumPics: string
    description: string
    serviceIds: string
    detailMobileHtml: string
    productSn: string
    promotionType: number
  }
  brand: PmsBrand
  skuStockList: PmsSkuStock[]
  productAttributeList: { id: number | string; name: string; type: number; inputList: string }[]
  productAttributeValueList: { id: number | string; productAttributeId: number | string; value: string }[]
  productFullReductionList: { id: number; fullPrice: number; reducePrice: number }[]
  productLadderList: { id: number; count: number; discount: number; price: number }[]
  couponList: SmsCoupon[]
}

const defaultBrand: PmsBrand = {
  id: '', name: '', firstLetter: '', logo: '', bigPic: '',
  brandStory: '', sort: 0, showStatus: 0, createdAt: '',
}

const productImages = ref<string[]>([])

const mockProduct = ref<MockProductDetail>({
  product: {
    id: '', name: '', subTitle: '', price: 0, originalPrice: 0,
    sale: 0, stock: 0, brandName: '', productCategoryName: '',
    pic: '', albumPics: '', description: '', serviceIds: '',
    detailMobileHtml: '', productSn: '', promotionType: 0,
  },
  brand: { ...defaultBrand },
  skuStockList: [],
  productAttributeList: [],
  productAttributeValueList: [],
  productFullReductionList: [],
  productLadderList: [],
  couponList: [],
})

/** 将 API SKU 列表映射为 skuStockList 格式 */
function mapSkuStockList(skus: Record<string, unknown>[]): PmsSkuStock[] {
  return skus.map((sku) => ({
    id: String(sku.id || ''),
    skuCode: (sku.skuCode || '') as string,
    price: (sku.price as number) || 0,
    stock: (sku.stock as number) || 0,
    promotionPrice: (sku.promotionPrice as number) || 0,
    spData: (sku.spec || sku.spData || '{}') as string,
    lockStock: (sku.lockStock as number) || 0,
    lowStock: (sku.lowStock as number) || 0,
    pic: (sku.pic || '') as string,
    productId: String(sku.productId || ''),
    sale: (sku.saleCount as number) || (sku.sale as number) || 0,
  }))
}

/** 从 API 响应加载商品数据 */
async function loadProduct() {
  const productId = route.params.id as string
  // 校验 UUID 格式, 过滤无效值 (包括字符串 "undefined")
  if (!productId || productId === 'undefined' || !/^[0-9a-f]{8}-[0-9a-f]{4}-/.test(productId)) return

  loading.value = true
  try {
    const data = await getProductDetailAPI(productId)

    // 图片列表
    const pics = (data.defaultPic || '') as string
    const albumPics = (data.albumPics || '') as string
    const allPics = [pics, ...albumPics.split(',').filter(Boolean)].filter(Boolean)
    productImages.value = allPics.length > 0 ? allPics : ['']

    // SKU
    const skus = (data.skus || []) as unknown as Record<string, unknown>[]
    const skuStockList = mapSkuStockList(skus)

    // 属性值
    const attrValues = data.attributeValues || []
    const productAttributeValueList = attrValues.map((av, i) => ({
      id: String(av.id || i + 1),
      productAttributeId: String(av.attributeId || av.productAttributeId || ''),
      value: (av.value || '') as string,
    }))

    // 从 SKU spec 提取属性维度
    const dimSet = new Map<string, Set<string>>()
    skuStockList.forEach((sku) => {
      let spec: Record<string, string> = {}
      try { spec = JSON.parse(sku.spData) } catch { /* ignore */ }
      Object.entries(spec).forEach(([k, v]) => {
        if (!dimSet.has(k)) dimSet.set(k, new Set())
        dimSet.get(k)!.add(v)
      })
    })
    const productAttributeList = Array.from(dimSet.entries()).map(([name, values], i) => ({
      id: i + 1, name, type: 0, inputList: Array.from(values).join(','),
    }))

    mockProduct.value = {
      product: {
        id: data.id,
        name: (data.name || '') as string,
        subTitle: (data.subTitle || '') as string,
        price: (data.price as number) || 0,
        originalPrice: (data.originalPrice as number) || 0,
        sale: data.saleCount || 0,
        stock: (data.stock as number) || 0,
        brandName: '',
        productCategoryName: '',
        pic: allPics[0] || '',
        albumPics: albumPics,
        description: (data.description || '') as string,
        serviceIds: (data.serviceIds || '') as string,
        detailMobileHtml: data.description || '',
        productSn: (data.productSn || '') as string,
        promotionType: (data.promotionType as number) || 0,
      },
      brand: { ...defaultBrand, id: data.brandId || '' },
      skuStockList,
      productAttributeList,
      productAttributeValueList,
      productFullReductionList: [],
      productLadderList: [],
      couponList: [],
    }

    // 默认选中第一个有库存的 SKU
    if (skuStockList.length > 0) {
      const firstInStock = skuStockList.find((s) => s.stock > 0)
      if (firstInStock) selectedSku.value = firstInStock
    }

    // 埋点：记录商品浏览
    if (productId) trackView(productId)
  } catch (err: any) {
    console.error('商品加载失败:', err?.message || err)
    error.value = err?.message || '商品加载失败'
  } finally {
    loading.value = false
  }
}

/** 加载评价列表 */
async function loadReviews(reset = false) {
  const productId = route.params.id as string
  if (!productId || productId === 'undefined') return

  if (reset) {
    reviewPage.value = 1
    reviewError.value = ''
  }

  const currentPage = reset ? 1 : reviewPage.value + 1

  reviewLoading.value = true
  try {
    const result = await listReviewsAPI({
      product_id: productId,
      page: currentPage,
      page_size: reviewPageSize,
    })
    if (reset) {
      reviews.value = result.items || []
    } else {
      reviews.value.push(...(result.items || []))
    }
    reviewTotal.value = result.total || 0
    reviewPage.value = currentPage
  } catch (err: any) {
    reviewError.value = err?.message || '评价加载失败, 请稍后重试'
  } finally {
    reviewLoading.value = false
  }
}

/** 加载更多评价 */
function loadMoreReviews() {
  loadReviews(false)
}

// ============================================================
// 状态管理
// ============================================================

/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref('')
/** 当前选中的 SKU */
const selectedSku = ref<PmsSkuStock | null>(null)
/** 购买数量 */
const quantity = ref(1)
/** 当前主图索引 */
const currentImageIndex = ref(0)
/** 详情 Tab 选中 — 支持 ?tab=reviews 直接定位到评价 */
const activeTab = ref<'detail' | 'params' | 'reviews'>(
  (route.query.tab as 'detail' | 'params' | 'reviews') === 'reviews' ? 'reviews' : 'detail'
)

// ── 评价相关状态 ──
const reviews = ref<ReviewItem[]>([])
const reviewLoading = ref(false)
const reviewError = ref('')
const reviewTotal = ref(0)
const reviewPage = ref(1)
const reviewPageSize = 10

/** 评价概览 */
const reviewAvgRating = computed(() => {
  if (reviews.value.length === 0) return 0
  const sum = reviews.value.reduce((acc, r) => acc + r.rating, 0)
  return Math.round((sum / reviews.value.length) * 10) / 10
})

/** 评价表单弹窗 */
const reviewFormVisible = ref(false)
const showReviewForm = () => {
  if (!memberStore.isLoggedIn) {
    router.push(`/login?redirect=/product/${route.params.id as string}`)
    return
  }
  reviewFormVisible.value = true
}
const onReviewSubmitted = () => {
  reviewFormVisible.value = false
  loadReviews(true)
}

/** 计算当前显示的主图 */
const currentMainImage = computed(() => {
  const skuImage = selectedSku.value?.pic
  if (skuImage && currentImageIndex.value === 0) return skuImage
  const imgs = productImages.value
  return imgs[currentImageIndex.value] || imgs[0] || ''
})

/** 格式化价格 */
const formatPrice = (price: number) => {
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Sanitized detail HTML — with image fallback and malformed-HTML hardening */
const sanitizedDetailHtml = computed(() => {
  let raw = mockProduct.value.product.detailMobileHtml
  if (!raw) return ''
  // 转义被尖括号包裹的裸 URL（如 <http://...>），防止浏览器解析为非法 tag 名
  raw = raw.replace(/<(https?:\/\/[^>]+)>/g, (_, url) => `&lt;${url}&gt;`)
  return DOMPurify.sanitize(raw)
})

// ============================================================
// SKU 规格选择逻辑
// ============================================================

/** 解析 SKU 规格数据 */
const parsedSkuSpecs = computed(() => {
  return mockProduct.value.skuStockList.map((sku) => {
    try {
      const specs = JSON.parse(sku.spData) as Record<string, string>
      return { sku, specs }
    } catch {
      return { sku, specs: {} as Record<string, string> }
    }
  })
})

/** 获取所有规格维度 */
const specDimensions = computed(() => {
  const dims = new Set<string>()
  parsedSkuSpecs.value.forEach(({ specs }) => {
    Object.keys(specs).forEach((k) => dims.add(k))
  })
  return Array.from(dims)
})

/** 获取某个维度的所有可选值 */
const getSpecValues = (dimension: string) => {
  const values = new Set<string>()
  parsedSkuSpecs.value.forEach(({ specs }) => {
    if (specs[dimension]) values.add(specs[dimension])
  })
  return Array.from(values)
}

/** 当前选中的规格组合 */
const selectedSpecs = ref<Record<string, string>>({})

const initSelectedSpecs = () => {
  const first = parsedSkuSpecs.value[0]
  if (first) selectedSpecs.value = { ...first.specs }
}
// 初始化 + 数据变化时重新初始化
watch(parsedSkuSpecs, (val) => {
  if (val.length > 0 && Object.keys(selectedSpecs.value).length === 0) {
    initSelectedSpecs()
  }
})

/** 切换到评价 tab 时加载评价数据 */
watch(activeTab, (tab) => {
  if (tab === 'reviews' && reviews.value.length === 0 && !reviewLoading.value) {
    loadReviews(true)
  }
})

/** 判断某个规格值是否被选中 */
const isSpecSelected = (dimension: string, value: string) => {
  return selectedSpecs.value[dimension] === value
}

/** 选择规格值 */
const selectSpec = (dimension: string, value: string) => {
  selectedSpecs.value[dimension] = value
  const matched = parsedSkuSpecs.value.find(({ specs }) => {
    return specDimensions.value.every(
      (dim) => selectedSpecs.value[dim] === specs[dim]
    )
  })
  if (matched) selectedSku.value = matched.sku
}

/** 判断某规格值是否存在对应 SKU */
const isSpecAvailable = (dimension: string, value: string) => {
  return parsedSkuSpecs.value.some(({ sku, specs }) => {
    if (sku.stock <= 0) return false
    return specDimensions.value.every((dim) => {
      if (dim === dimension) return specs[dim] === value
      return selectedSpecs.value[dim] === specs[dim]
    })
  })
}

/** 获取某规格值对应的 SKU 图片（用于图片色块展示，如颜色规格） */
const getSkuImageForSpec = (dimension: string, value: string): string => {
  const entry = parsedSkuSpecs.value.find(
    ({ specs }) => specs[dimension] === value
  )
  return entry?.sku.pic || ''
}

// ============================================================
// 放大镜效果
// ============================================================

const magnifierRef = ref<HTMLDivElement | null>(null)
const mainImageRef = ref<HTMLDivElement | null>(null)
const showMagnifier = ref(false)
const magnifierPosition = ref({ x: 0, y: 0 })
const zoomLevel = 2.5

const handleMouseMove = (e: MouseEvent) => {
  if (!mainImageRef.value) return
  const rect = mainImageRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
    showMagnifier.value = false
    return
  }

  showMagnifier.value = true
  magnifierPosition.value = { x, y }

  if (magnifierRef.value) {
    const lensSize = 120
    const bgX = (x / rect.width) * 100
    const bgY = (y / rect.height) * 100
    magnifierRef.value.style.backgroundPosition = `${bgX}% ${bgY}%`
    magnifierRef.value.style.backgroundSize = `${rect.width * zoomLevel}px ${rect.height * zoomLevel}px`

    const lensX = Math.max(0, Math.min(x - lensSize / 2, rect.width - lensSize))
    const lensY = Math.max(0, Math.min(y - lensSize / 2, rect.height - lensSize))
    magnifierRef.value.style.left = `${lensX}px`
    magnifierRef.value.style.top = `${lensY}px`
  }
}

const handleMouseLeave = () => {
  showMagnifier.value = false
}

// ============================================================
// 操作按钮
// ============================================================

const productId = computed(() => String(mockProduct.value.product.id || route.params.id))

/** 添加到购物车 */
const handleAddToCart = async () => {
  if (!selectedSku.value) return
  try {
    await addCartAPI({
      product_id: productId.value,
      sku_id: String(selectedSku.value.id),
      quantity: quantity.value,
    })
    await cartStore.fetchCartList()
    const toast = document.createElement('div')
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium animate-fade-in'
    toast.textContent = '已成功添加到购物车'
    document.body.appendChild(toast)
    setTimeout(() => toast.remove(), 2000)
  } catch {
    const toast = document.createElement('div')
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium'
    toast.textContent = '添加到购物车失败，请重试'
    document.body.appendChild(toast)
    setTimeout(() => toast.remove(), 2000)
  }
}

/** 立即购买 */
const buying = ref(false)
const handleBuyNow = async () => {
  if (!memberStore.isLoggedIn) {
    router.push(`/login?redirect=/product/${productId.value}`)
    return
  }
  if (!selectedSku.value) {
    showToast('请选择商品规格', 'error')
    return
  }
  buying.value = true
  try {
    await addCartAPI({
      product_id: productId.value,
      sku_id: String(selectedSku.value.id),
      quantity: quantity.value,
    })
    await cartStore.fetchCartList()
    router.push('/order-confirm')
  } catch {
    showToast('操作失败，请重试', 'error')
  } finally {
    buying.value = false
  }
}

/** 收藏状态 */
const isFavorited = ref(false)
const isFavoriting = ref(false)

/** 轻量 Toast 提示 */
function showToast(msg: string, type: 'success' | 'error' = 'success') {
  const toast = document.createElement('div')
  toast.className = `fixed top-20 left-1/2 -translate-x-1/2 px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium animate-fade-in ${type === 'error' ? 'bg-red-600' : 'bg-green-600'} text-white`
  toast.textContent = msg
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 2000)
}

/** 切换收藏 */
const handleToggleFavorite = async () => {
  if (!memberStore.isLoggedIn) {
    router.push(`/login?redirect=/product/${productId.value}`)
    return
  }
  if (isFavoriting.value) return
  isFavoriting.value = true
  try {
    if (isFavorited.value) {
      await deleteProductCollectionAPI({ productId: productId.value })
      isFavorited.value = false
      showToast('已取消收藏')
    } else {
      await createProductCollectionAPI({ productId: productId.value })
      isFavorited.value = true
      showToast('收藏成功')
    }
  } catch (err: any) {
    showToast(err?.message || '操作失败', 'error')
  } finally {
    isFavoriting.value = false
  }
}

/** 检查商品是否已收藏 */
async function checkFavoriteStatus() {
  if (!memberStore.isLoggedIn) return
  try {
    const res = await fetchProductCollectionListAPI({ pageNum: 1, pageSize: 100 }) as unknown as { items: { productId: string }[] }
    const items = res?.items || []
    isFavorited.value = items.some(item => String(item.productId) === productId.value)
  } catch { /* ignore */ }
}

/** 领取优惠券 */
const receivedCoupons = ref<Set<string>>(new Set())
const receiveCoupon = (couponId: string) => {
  receivedCoupons.value.add(couponId)
  const toast = document.createElement('div')
  toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium'
  toast.textContent = '优惠券领取成功'
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 2000)
}

/** 返回上一个打开页面；无历史来源时回到商品分类页 */
function goBack() {
  const historyState = window.history.state as { back?: string | null } | null
  if (historyState?.back) {
    router.back()
    return
  }
  router.push('/category')
}

// ============================================================
// 生命周期
// ============================================================

onMounted(() => {
  loadProduct().then(() => {
    checkFavoriteStatus()
    loadReviews(true)
  })
})

onUnmounted(() => {
  // 清理
})
</script>

<template>
  <div class="product-detail-page max-w-7xl mx-auto px-4 py-6">
    <div class="flex items-center gap-3 mb-5">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium text-gray-600 shadow-sm transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-600"
        @click="goBack"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        返回
      </button>

      <!-- 面包屑导航 -->
      <nav class="flex min-w-0 flex-1 items-center gap-2 text-sm text-gray-500">
        <button class="hover:text-brand-600 transition-colors" @click="router.push('/')">首页</button>
        <span class="text-gray-300">/</span>
        <button class="hover:text-brand-600 transition-colors" @click="router.push('/category')">{{ mockProduct.product.productCategoryName || '全部分类' }}</button>
        <span class="text-gray-300">/</span>
        <button
          v-if="mockProduct.brand.id"
          class="hover:text-brand-600 transition-colors"
          @click="router.push(`/brand/${mockProduct.brand.id}`)"
        >
          {{ mockProduct.product.brandName }}
        </button>
        <span v-if="mockProduct.brand.id" class="text-gray-300">/</span>
        <span class="text-gray-700 truncate max-w-md">{{ mockProduct.product.name || '商品详情' }}</span>
      </nav>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-32">
      <div class="flex items-center gap-3 text-gray-400">
        <svg class="animate-spin h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span>商品加载中...</span>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="flex items-center justify-center py-32">
      <div class="text-center">
        <p class="text-red-500 text-lg mb-4">{{ error }}</p>
        <button class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors" @click="loadProduct">重新加载</button>
      </div>
    </div>

    <template v-else>
      <!-- ============================================================ -->
      <!-- 淘宝式左右分栏：左 54% 图片+详情 | 右 46% 购买面板 sticky -->
      <!-- ============================================================ -->
      <div class="flex gap-5 items-start">
        <!-- ====== 左侧 54%：图片 + Tab 详情 ====== -->
        <div class="w-[54%] flex-shrink-0 space-y-5">
          <!-- 图片卡片 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <!-- 主图 + 放大镜 -->
            <div
              ref="mainImageRef"
              class="relative w-full aspect-square rounded-lg bg-gray-50 overflow-hidden cursor-crosshair mb-3"
              @mousemove="handleMouseMove"
              @mouseleave="handleMouseLeave"
            >
              <img
                :src="currentMainImage"
                :alt="mockProduct.product.name"
                class="w-full h-full object-cover select-none"
                draggable="false"
              />
              <!-- 放大镜镜头 -->
              <div
                v-show="showMagnifier"
                ref="magnifierRef"
                class="absolute w-[120px] h-[120px] border-2 border-white/80 rounded-lg shadow-lg pointer-events-none"
                :style="{
                  backgroundImage: `url(${currentMainImage})`,
                  backgroundRepeat: 'no-repeat',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                }"
              />
              <!-- 销量角标 -->
              <div v-if="mockProduct.product.sale > 0" class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/40 to-transparent pt-8 pb-2 px-3">
                <span class="text-white text-xs">已售 {{ mockProduct.product.sale }}+</span>
              </div>
            </div>

            <!-- 缩略图列表 -->
            <div v-if="productImages.length > 1" class="flex gap-2 overflow-x-auto pb-1">
              <button
                v-for="(img, index) in productImages"
                :key="index"
                :class="[
                  'w-[72px] h-[72px] rounded-md overflow-hidden border-2 transition-all flex-shrink-0',
                  currentImageIndex === index
                    ? 'border-brand-600 ring-1 ring-brand-600'
                    : 'border-gray-200 hover:border-gray-400 opacity-80 hover:opacity-100',
                ]"
                @mouseenter="currentImageIndex = index"
              >
                <img :src="img" :alt="`图片${index + 1}`" class="w-full h-full object-cover" />
              </button>
            </div>

            <!-- 底部分享 -->
            <div class="flex items-center gap-6 mt-3 pt-3 border-t border-gray-100 text-sm text-gray-400">
              <button class="flex items-center gap-1.5 hover:text-brand-600 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                分享
              </button>
              <span class="text-gray-200">|</span>
              <button class="flex items-center gap-1.5 hover:text-brand-600 transition-colors" @click="router.push('/')">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                店铺首页
              </button>
            </div>
          </div>

          <!-- Tab 卡片 — 商品详情/规格参数/用户评价 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <!-- Tab 头部 -->
            <div class="flex border-b border-gray-100 bg-gray-50/50">
              <button
                v-for="tab in [
                  { key: 'detail' as const, label: '商品详情' },
                  ...(mockProduct.productAttributeList.length > 0 ? [{ key: 'params' as const, label: '规格参数' }] : []),
                  { key: 'reviews' as const, label: '用户评价' },
                ]"
                :key="tab.key"
                :class="[
                  'px-8 py-3.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                  activeTab === tab.key
                    ? 'text-brand-600 border-brand-600 bg-white'
                    : 'text-gray-500 border-transparent hover:text-gray-700',
                ]"
                @click="activeTab = tab.key"
              >{{ tab.key === 'reviews' && reviewTotal > 0 ? `${tab.label} (${reviewTotal})` : tab.label }}</button>
            </div>

            <!-- Tab 内容 -->
            <div class="p-6">
              <!-- 商品详情 -->
              <div v-if="activeTab === 'detail'">
                <!-- 富文本 HTML 渲染 (sanitized to prevent XSS) -->
                <div v-if="sanitizedDetailHtml" v-html="sanitizedDetailHtml" class="detail-html prose max-w-none" />
                <div v-else class="flex flex-col items-center justify-center py-16 text-gray-400 text-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>暂无详情内容</p>
                </div>
              </div>

              <!-- 规格参数 -->
              <div v-if="activeTab === 'params'">
                <table class="w-full text-sm">
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="attr in mockProduct.productAttributeList" :key="attr.id" class="hover:bg-gray-50">
                      <td class="py-3 px-4 text-gray-500 w-28 bg-gray-50 font-medium">{{ attr.name }}</td>
                      <td class="py-3 px-4 text-gray-900">{{ attr.inputList }}</td>
                    </tr>
                    <tr v-if="mockProduct.product.productSn" class="hover:bg-gray-50">
                      <td class="py-3 px-4 text-gray-500 w-28 bg-gray-50 font-medium">商品编号</td>
                      <td class="py-3 px-4 text-gray-900">{{ mockProduct.product.productSn }}</td>
                    </tr>
                    <tr v-if="mockProduct.brand.name || mockProduct.product.brandName" class="hover:bg-gray-50">
                      <td class="py-3 px-4 text-gray-500 w-28 bg-gray-50 font-medium">品牌</td>
                      <td class="py-3 px-4 text-gray-900">{{ mockProduct.brand.name || mockProduct.product.brandName }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 用户评价 -->
              <div v-if="activeTab === 'reviews'">
                <!-- 评价头部：写评价按钮 -->
                <div class="flex items-center justify-between mb-4">
                  <span class="text-sm text-gray-500">
                    {{ reviews.length > 0 ? `共 ${reviewTotal} 条` : '' }}
                  </span>
                  <button
                    v-if="memberStore.isLoggedIn"
                    class="px-4 py-1.5 text-xs font-medium text-brand-600 border border-brand-600 rounded-full hover:bg-brand-50 transition-colors"
                    @click="showReviewForm"
                  >
                    写评价
                  </button>
                </div>

                <!-- 加载中 -->
                <div v-if="reviewLoading && reviews.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400 text-sm">
                  <div class="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin mb-3" />
                  <p>加载中...</p>
                </div>

                <!-- 加载失败 -->
                <div v-else-if="reviewError && reviews.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400 text-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <p class="text-red-500">{{ reviewError }}</p>
                  <button class="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium" @click="loadReviews(true)">点击重试</button>
                </div>

                <!-- 空状态 -->
                <div v-else-if="!reviewLoading && reviews.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400 text-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <p>暂无评价</p>
                  <p class="text-xs mt-1">成为第一个评价的人吧</p>
                </div>

                <!-- 评价列表 -->
                <div v-else class="space-y-4">
                  <div v-for="review in reviews" :key="review.id" class="border-b border-gray-100 pb-4 last:border-b-0 last:pb-0">
                    <div class="flex items-start gap-3">
                      <!-- 头像 -->
                      <div class="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 text-sm font-medium flex-shrink-0">
                        {{ review.isAnonymous ? '匿' : '用' }}
                      </div>
                      <div class="flex-1 min-w-0">
                        <!-- 顶行：用户名 + 评分 + 时间 -->
                        <div class="flex items-center gap-3 mb-1.5">
                          <span class="text-sm font-medium text-gray-900">
                            {{ review.isAnonymous ? '匿名用户' : '用户' }}
                          </span>
                          <!-- 星级 -->
                          <div class="flex items-center gap-0.5">
                            <svg v-for="i in 5" :key="i" xmlns="http://www.w3.org/2000/svg"
                              :class="['w-3.5 h-3.5', i <= review.rating ? 'text-amber-400' : 'text-gray-200']"
                              viewBox="0 0 20 20" fill="currentColor">
                              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                          </div>
                          <span class="text-xs text-gray-400 ml-auto">
                            {{ new Date(review.createdAt).toLocaleDateString('zh-CN') }}
                          </span>
                        </div>
                        <!-- 评价内容 -->
                        <p v-if="review.content" class="text-sm text-gray-700 leading-relaxed">{{ review.content }}</p>
                        <!-- 评价图片 -->
                        <div v-if="review.images" class="flex gap-2 mt-2">
                          <img
                            v-for="(img, idx) in review.images.split(',').filter(Boolean)"
                            :key="idx"
                            :src="img"
                            class="w-16 h-16 object-cover rounded-lg border border-gray-100 cursor-pointer hover:opacity-80 transition-opacity"
                          />
                        </div>
                        <!-- 商家回复 -->
                        <div v-if="review.reply" class="mt-2 bg-gray-50 rounded-lg px-3 py-2 text-sm">
                          <span class="text-gray-500 font-medium">商家回复：</span>
                          <span class="text-gray-600">{{ review.reply }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 加载更多 -->
                  <div v-if="reviews.length < reviewTotal" class="text-center pt-2">
                    <button
                      class="text-sm text-brand-600 hover:text-brand-700 font-medium disabled:text-gray-300"
                      :disabled="reviewLoading"
                      @click="loadMoreReviews"
                    >
                      {{ reviewLoading ? '加载中...' : '加载更多评价' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ====== 右侧 46%：购买面板（sticky，独立滚动） ====== -->
        <div class="w-[46%] flex-shrink-0 sticky top-6 self-start bg-white rounded-xl shadow-sm border border-gray-100 p-6"
          style="max-height: calc(100vh - 48px); overflow-y: auto;">
          <!-- 商品标题 -->
          <h1 class="text-xl font-bold text-gray-900 leading-7 mb-1">
            {{ mockProduct.product.name }}
          </h1>

          <!-- 副标题 -->
          <p v-if="mockProduct.product.subTitle" class="text-sm text-brand-600 mb-4 leading-5">
            {{ mockProduct.product.subTitle }}
          </p>

          <!-- 价格区 — 淘宝红底 -->
          <div class="bg-gradient-to-r from-red-50 to-pink-50 rounded-xl px-5 py-4 mb-5">
            <div class="flex items-baseline gap-2 mb-3">
              <span class="text-3xl font-extrabold text-red-500">
                <span class="text-lg">&yen;</span>{{ formatPrice(selectedSku?.promotionPrice || selectedSku?.price || mockProduct.product.price) }}
              </span>
              <span v-if="mockProduct.product.originalPrice && mockProduct.product.originalPrice > (selectedSku?.price || mockProduct.product.price)" class="text-sm text-gray-400 line-through">
                &yen;{{ formatPrice(mockProduct.product.originalPrice) }}
              </span>
              <span v-if="mockProduct.product.originalPrice && mockProduct.product.originalPrice > (selectedSku?.price || mockProduct.product.price)"
                class="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full font-bold">
                {{ Math.round(((mockProduct.product.originalPrice - (selectedSku?.price || mockProduct.product.price)) / mockProduct.product.originalPrice) * 100) }}%OFF
              </span>
            </div>
            <div class="flex items-center gap-5 text-xs text-gray-500">
              <span>销量 <span class="text-gray-900 font-semibold ml-0.5">{{ mockProduct.product.sale || 0 }}</span></span>
              <span class="text-gray-200">|</span>
              <span>库存 <span :class="(selectedSku?.stock || 0) > 20 ? 'text-gray-900' : 'text-red-500'" class="font-semibold ml-0.5">{{ selectedSku?.stock ?? '--' }}</span> 件</span>
              <span class="text-gray-200">|</span>
              <span>浙江杭州 <span class="ml-1 text-gray-400">发货</span></span>
            </div>
          </div>

          <!-- 评分概览 -->
          <div v-if="reviewTotal > 0" class="flex items-center gap-3 px-5 py-3 mb-5 bg-gray-50 rounded-xl text-sm">
            <span class="text-xl font-bold text-amber-500">{{ reviewAvgRating || '-' }}</span>
            <div class="flex items-center gap-0.5">
              <svg v-for="i in 5" :key="i" xmlns="http://www.w3.org/2000/svg"
                :class="['w-4 h-4', i <= Math.round(reviewAvgRating) ? 'text-amber-400' : 'text-gray-200']"
                viewBox="0 0 20 20" fill="currentColor">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            </div>
            <span class="text-gray-500 text-xs">{{ reviewTotal }} 条评价</span>
          </div>

          <!-- 优惠 & 配送 -->
          <div class="bg-gray-50 rounded-lg px-4 py-3 mb-5 space-y-2 text-sm">
            <div v-for="fr in mockProduct.productFullReductionList" :key="fr.id" class="flex items-center gap-2">
              <span class="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0">满减</span>
              <span class="text-red-600">满{{ fr.fullPrice }}减{{ fr.reducePrice }}</span>
            </div>
            <div v-if="mockProduct.couponList.length > 0" class="flex items-center gap-2">
              <span class="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0">领券</span>
              <span class="text-red-600">领券减{{ mockProduct.couponList[0]?.amount || '' }}元</span>
              <span class="text-gray-400 flex-1 text-right">共{{ mockProduct.couponList.length }}张 &gt;</span>
            </div>
            <!-- 阶梯优惠 -->
            <div v-for="ladder in mockProduct.productLadderList" :key="ladder.id" class="flex items-center gap-2">
              <span class="bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0">阶梯</span>
              <span class="text-orange-600">满{{ ladder.count }}件打{{ (ladder.discount * 10).toFixed(1) }}折</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-gray-500 pt-1 border-t border-gray-200">
              <span class="text-green-600">✓</span> 正品保障
              <span class="text-green-600 ml-2">✓</span> 7天无理由
              <span class="text-green-600 ml-2">✓</span> 极速退款
            </div>
          </div>

          <!-- SKU 规格选择 — 图片色块或文字按钮 -->
          <div v-if="specDimensions.length > 0" class="mb-5 space-y-4">
            <div v-for="dimension in specDimensions" :key="dimension">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-sm text-gray-700 font-medium">{{ dimension }}</span>
                <span class="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{{ selectedSpecs[dimension] || '未选择' }}</span>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="value in getSpecValues(dimension)"
                  :key="value"
                  :disabled="!isSpecAvailable(dimension, value)"
                  :title="!isSpecAvailable(dimension, value) ? '已售罄' : value"
                  :class="[
                    'relative transition-all',
                    isSpecSelected(dimension, value)
                      ? 'ring-2 ring-brand-600 ring-offset-1 rounded-lg'
                      : '',
                  ]"
                  @click="selectSpec(dimension, value)"
                >
                  <img
                    v-if="getSkuImageForSpec(dimension, value)"
                    :src="getSkuImageForSpec(dimension, value)"
                    :alt="value"
                    :class="[
                      'w-12 h-12 object-cover rounded-lg border-2 transition-colors',
                      isSpecSelected(dimension, value) ? 'border-brand-600' : 'border-gray-200 hover:border-gray-400',
                      !isSpecAvailable(dimension, value) ? 'opacity-30' : '',
                    ]"
                  />
                  <span
                    v-else
                    :class="[
                      'inline-block px-4 py-2 text-sm rounded-md border transition-all select-none',
                      isSpecSelected(dimension, value)
                        ? 'border-brand-600 text-brand-600 bg-brand-50 font-medium shadow-sm'
                        : isSpecAvailable(dimension, value)
                          ? 'border-gray-200 text-gray-700 hover:border-brand-300 hover:text-brand-600 cursor-pointer'
                          : 'border-gray-100 text-gray-300 cursor-not-allowed bg-gray-50 line-through',
                    ]"
                  >{{ value }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- 数量选择 -->
          <div class="flex items-center gap-3 mb-6">
            <span class="text-sm text-gray-700 font-medium w-10 flex-shrink-0">数量</span>
            <div class="flex items-center border border-gray-300 rounded-md h-10">
              <button
                class="w-9 h-full flex items-center justify-center text-gray-500 hover:text-brand-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                :disabled="quantity <= 1"
                @click="quantity--"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4" />
                </svg>
              </button>
              <input
                v-model.number="quantity"
                type="number"
                min="1"
                :max="Math.min(selectedSku?.stock || 999, 999)"
                class="w-16 h-full text-center text-sm font-medium border-x border-gray-300 outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                @change="if (quantity < 1) quantity = 1; if (quantity > (selectedSku?.stock || 999)) quantity = selectedSku?.stock || 999"
              />
              <button
                class="w-9 h-full flex items-center justify-center text-gray-500 hover:text-brand-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                :disabled="quantity >= (selectedSku?.stock || 999)"
                @click="quantity++"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
            <span v-if="(selectedSku?.stock || 0) > 0 && (selectedSku?.stock || 0) <= 20" class="text-xs text-red-400">仅剩 {{ selectedSku?.stock }} 件</span>
          </div>

          <!-- 操作按钮 — 收藏 + 加入购物车 + 领券购买 -->
          <div class="flex items-stretch gap-3 mb-5">
            <!-- 收藏 -->
            <button
              :disabled="isFavoriting"
              class="w-14 flex-shrink-0 flex flex-col items-center justify-center gap-0.5 rounded-lg border border-gray-200 text-gray-500 hover:text-brand-600 hover:border-brand-300 transition-colors disabled:opacity-50"
              @click="handleToggleFavorite"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" :fill="isFavorited ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span class="text-[10px]">{{ isFavorited ? '已收藏' : '收藏' }}</span>
            </button>

            <!-- 加入购物车 -->
            <button
              class="flex-1 h-12 bg-gradient-to-r from-orange-500 to-red-500 text-white font-bold text-base rounded-2xl hover:from-orange-600 hover:to-red-600 transition-all flex items-center justify-center gap-2 shadow-md shadow-red-200 active:scale-[0.98]"
              @click="handleAddToCart"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              加入购物车
            </button>

            <!-- 领券购买 -->
            <button
              :disabled="buying"
              class="flex-1 h-12 bg-gradient-to-r from-red-500 to-pink-500 text-white font-bold text-base rounded-2xl hover:from-red-600 hover:to-pink-600 transition-all flex items-center justify-center gap-2 shadow-md shadow-pink-200 active:scale-[0.98] disabled:opacity-60"
              @click="handleBuyNow"
            >
              <svg v-if="!buying" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
              </svg>
              <svg v-else class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              {{ buying ? '处理中...' : '领券购买' }}
            </button>
          </div>

          <p class="text-xs text-gray-400 text-center">支持7天无理由退换 · 48小时内发货 · 全国联保</p>
        </div>
      </div>
    </template>
  </div>

  <!-- 评价表单弹窗 -->
  <ReviewForm
    :product-id="productId"
    :visible="reviewFormVisible"
    @update:visible="reviewFormVisible = $event"
    @submitted="onReviewSubmitted"
  />
</template>

<style scoped>
/* 放大镜 */
.magnifier-lens {
  background-repeat: no-repeat;
  backdrop-filter: blur(1px);
}

/* 渐入动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: translate(-50%, -10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

/* 行省略 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 详情富文本渲染 — 确保图片和排版正常 */
.detail-html :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 12px 0;
}
.detail-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}
.detail-html :deep(td),
.detail-html :deep(th) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}
.detail-html :deep(p) {
  margin: 8px 0;
  line-height: 1.8;
}

/* 右侧面板滚动条 */
.sticky {
  scrollbar-width: thin;
  scrollbar-color: #e5e7eb transparent;
}
.sticky::-webkit-scrollbar {
  width: 4px;
}
.sticky::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 4px;
}
.sticky::-webkit-scrollbar-track {
  background: transparent;
}
</style>
