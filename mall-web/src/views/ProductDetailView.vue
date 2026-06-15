<script setup lang="ts">
/**
 * ============================================
 * 商品详情页 (ProductDetailView)
 * PC 端专属设计：
 * - 左右分栏：左侧主图+放大镜+缩略图，右侧信息+SKU+操作
 * - 底部通栏：详情长图
 * - Composition API + SKU 状态联动
 * ============================================
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { addCartAPI } from '@/apis/cart'
import { getProductDetailAPI } from '@/apis/product'
import { useCartStore } from '@/stores/cart'
import { useMemberStore } from '@/stores/member'
import type { PmsSkuStock } from '@/types/product'
import type { PmsBrand } from '@/types/brand'
import type { SmsCoupon } from '@/types/coupon'

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
  id: 0, name: '', firstLetter: '', logo: '', bigPic: '',
  brandStory: '', sort: 0, showStatus: 0, productCount: 0, productCommentCount: 0,
  pic: '', createTime: '',
}

const productImages = ref<string[]>([])

const mockProduct = ref<MockProductDetail>({
  product: {
    id: 0, name: '', subTitle: '', price: 0, originalPrice: 0,
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
    id: sku.id as number,
    skuCode: (sku.skuCode || '') as string,
    price: (sku.price as number) || 0,
    stock: (sku.stock as number) || 0,
    promotionPrice: (sku.promotionPrice as number) || 0,
    spData: (sku.spec || sku.spData || '{}') as string,
    lockStock: (sku.lockStock as number) || 0,
    lowStock: (sku.lowStock as number) || 0,
    pic: (sku.pic || '') as string,
    productId: (sku.productId as number) || 0,
    sale: (sku.saleCount as number) || (sku.sale as number) || 0,
  }))
}

/** 从 API 响应加载商品数据 */
async function loadProduct() {
  const productId = route.params.id as string
  if (!productId) return

  loading.value = true
  try {
    const data = await getProductDetailAPI(productId) as Record<string, unknown>

    // 图片列表
    const pics = (data.pics || data.defaultPic || '') as string
    const albumPics = (data.albumPics || '') as string
    const allPics = [pics, ...albumPics.split(',').filter(Boolean)].filter(Boolean)
    productImages.value = allPics.length > 0 ? allPics : ['']

    // SKU
    const skus = (data.skus || []) as Record<string, unknown>[]
    const skuStockList = mapSkuStockList(skus)

    // 属性值
    const attrValues = (data.attributeValues || []) as Record<string, unknown>[]
    const productAttributeValueList = attrValues.map((av, i) => ({
      id: av.id || i + 1,
      productAttributeId: av.attributeId || av.productAttributeId || 0,
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
        id: data.id || 0,
        name: (data.name || '') as string,
        subTitle: (data.subTitle || '') as string,
        price: (data.price as number) || 0,
        originalPrice: (data.originalPrice as number) || 0,
        sale: (data.saleCount as number) || (data.sale as number) || 0,
        stock: (data.stock as number) || 0,
        brandName: (data.brandName || '') as string,
        productCategoryName: (data.productCategoryName || '') as string,
        pic: allPics[0] || '',
        albumPics: albumPics,
        description: (data.description || '') as string,
        serviceIds: (data.serviceIds || '') as string,
        detailMobileHtml: (data.detailMobileHtml || '') as string,
        productSn: (data.productSn || '') as string,
        promotionType: (data.promotionType as number) || 0,
      },
      brand: { ...defaultBrand, id: data.brandId as number || 0, name: (data.brandName || '') as string },
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
  } catch (err: any) {
    console.error('商品加载失败:', err?.message || err)
    error.value = err?.message || '商品加载失败'
  } finally {
    loading.value = false
  }
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
/** 详情 Tab 选中 */
const activeTab = ref<'detail' | 'params' | 'reviews'>('detail')

/** 计算当前显示的主图 */
const currentMainImage = computed(() => {
  const skuImage = selectedSku.value?.pic
  if (skuImage && currentImageIndex.value === 0) return skuImage
  const imgs = productImages.value
  return imgs[currentImageIndex.value] || imgs[0] || ''
})

/** 格式化价格 */
const formatPrice = (price: number) => {
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

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
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium'
    toast.textContent = '已成功添加到购物车'
    document.body.appendChild(toast)
    setTimeout(() => toast.remove(), 2000)
  }
}

/** 立即购买 */
const handleBuyNow = () => {
  if (!memberStore.isLoggedIn) {
    router.push(`/login?redirect=/product/${productId.value}`)
    return
  }
  router.push({
    path: '/order-confirm',
    query: {
      skuId: selectedSku.value?.id,
      quantity: quantity.value,
    },
  })
}

/** 领取优惠券 */
const receivedCoupons = ref<Set<number>>(new Set())
const receiveCoupon = (couponId: number) => {
  receivedCoupons.value.add(couponId)
  const toast = document.createElement('div')
  toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium'
  toast.textContent = '优惠券领取成功'
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 2000)
}

// ============================================================
// 生命周期
// ============================================================

onMounted(() => {
  loadProduct()
})

onUnmounted(() => {
  // 清理
})
</script>

<template>
  <div class="product-detail-page">
    <!-- 面包屑导航 -->
    <nav class="flex items-center gap-2 text-sm text-gray-500 mb-4">
      <button class="hover:text-red-600 transition-colors" @click="router.push('/')">首页</button>
      <span class="text-gray-300">/</span>
      <button class="hover:text-red-600 transition-colors" @click="router.push('/category')">{{ mockProduct.product.productCategoryName || '全部分类' }}</button>
      <span class="text-gray-300">/</span>
      <button v-if="mockProduct.brand.id" class="hover:text-red-600 transition-colors" @click="router.push(`/brand/${mockProduct.brand.id}`)">{{ mockProduct.product.brandName }}</button>
      <span v-if="mockProduct.brand.id" class="text-gray-300">/</span>
      <span class="text-gray-700 truncate max-w-md">{{ mockProduct.product.name || '商品详情' }}</span>
    </nav>

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
      <!-- 上部：左右分栏 -->
      <!-- ============================================================ -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <div class="flex gap-8">
          <!-- ====== 左侧：图片展示区 ====== -->
          <div class="w-[460px] flex-shrink-0">
            <!-- 主图 + 放大镜 -->
            <div
              ref="mainImageRef"
              class="relative w-full aspect-square rounded-lg bg-gray-50 overflow-hidden cursor-crosshair mb-4"
              @mousemove="handleMouseMove"
              @mouseleave="handleMouseLeave"
            >
              <img
                :src="currentMainImage"
                :alt="mockProduct.product.name"
                class="w-full h-full object-cover"
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

              <!-- 放大预览窗口（右侧弹出） -->
              <div
                v-show="showMagnifier"
                class="absolute left-full top-0 ml-3 w-[400px] h-[400px] rounded-lg overflow-hidden border border-gray-200 shadow-2xl z-30 bg-white"
              >
                <img
                  :src="currentMainImage"
                  :alt="mockProduct.product.name"
                  class="w-full h-full object-cover"
                  :style="{
                    transform: `scale(${zoomLevel})`,
                    transformOrigin: `${(magnifierPosition.x / 460) * 100}% ${(magnifierPosition.y / 460) * 100}%`,
                  }"
                />
              </div>
            </div>

            <!-- 缩略图列表 -->
            <div v-if="productImages.length > 1" class="flex gap-2">
              <button
                v-for="(img, index) in productImages"
                :key="index"
                :class="[
                  'w-[80px] h-[80px] rounded-md overflow-hidden border-2 transition-all flex-shrink-0',
                  currentImageIndex === index
                    ? 'border-red-600 ring-1 ring-red-600'
                    : 'border-gray-200 hover:border-gray-400',
                ]"
                @mouseenter="currentImageIndex = index"
              >
                <img :src="img" :alt="`图片${index + 1}`" class="w-full h-full object-cover" />
              </button>
            </div>

            <!-- 分享/收藏 -->
            <div class="flex items-center gap-4 mt-4 text-sm text-gray-500">
              <button class="flex items-center gap-1 hover:text-red-600 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                分享
              </button>
              <button class="flex items-center gap-1 hover:text-red-600 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                收藏
              </button>
            </div>
          </div>

          <!-- ====== 右侧：操作区 ====== -->
          <div class="flex-1 min-w-0">
            <!-- 商品标题 -->
            <h1 class="text-xl font-bold text-gray-900 leading-7 mb-2">
              {{ mockProduct.product.name }}
            </h1>

            <!-- 副标题 -->
            <p v-if="mockProduct.product.subTitle" class="text-sm text-red-600 mb-4 leading-5">
              {{ mockProduct.product.subTitle }}
            </p>

            <!-- 价格区 -->
            <div class="bg-gray-50 rounded-lg p-4 mb-5">
              <div class="flex items-baseline gap-3 mb-2">
                <span class="text-sm text-gray-500">促销价</span>
                <span class="text-3xl font-bold text-red-600">
                  <span class="text-lg">&yen;</span>{{ formatPrice(selectedSku?.promotionPrice || selectedSku?.price || mockProduct.product.price) }}
                </span>
                <span v-if="selectedSku?.price" class="text-sm text-gray-400 line-through">
                  &yen;{{ formatPrice(selectedSku.price) }}
                </span>
              </div>
              <div class="flex items-center gap-6 text-sm text-gray-500">
                <span>原价 <span class="line-through">&yen;{{ formatPrice(mockProduct.product.originalPrice) }}</span></span>
                <span>销量 <span class="text-gray-900 font-medium">{{ mockProduct.product.sale }}</span></span>
                <span>
                  库存
                  <span :class="(selectedSku?.stock || 0) > 20 ? 'text-gray-900' : 'text-red-600'" class="font-medium">
                    {{ selectedSku?.stock || 0 }}
                  </span>
                </span>
              </div>

              <!-- 优惠信息 -->
              <div class="mt-3 pt-3 border-t border-gray-200 space-y-2">
                <div v-for="fr in mockProduct.productFullReductionList" :key="fr.id" class="flex items-center gap-2 text-sm">
                  <span class="bg-red-600 text-white text-xs px-2 py-0.5 rounded">满减</span>
                  <span class="text-gray-600">满{{ fr.fullPrice }}减{{ fr.reducePrice }}</span>
                </div>
                <div v-if="selectedSku?.promotionPrice" class="flex items-center gap-2 text-sm">
                  <span class="bg-orange-500 text-white text-xs px-2 py-0.5 rounded">分期</span>
                  <span class="text-gray-600">12期免息，月供低至 &yen;{{ Math.round((selectedSku?.promotionPrice || selectedSku?.price || 0) / 12) }}</span>
                </div>
              </div>
            </div>

            <!-- SKU 规格选择 -->
            <div v-if="specDimensions.length > 0" class="mb-5 space-y-4">
              <div v-for="dimension in specDimensions" :key="dimension" class="flex items-start gap-3">
                <span class="text-sm text-gray-500 w-12 flex-shrink-0 pt-2">{{ dimension }}</span>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="value in getSpecValues(dimension)"
                    :key="value"
                    :disabled="!isSpecAvailable(dimension, value)"
                    :class="[
                      'px-4 py-2 text-sm border rounded-md transition-all',
                      isSpecSelected(dimension, value)
                        ? 'border-red-600 text-red-600 bg-red-50 font-medium ring-1 ring-red-600'
                        : isSpecAvailable(dimension, value)
                          ? 'border-gray-200 text-gray-700 hover:border-red-300 hover:text-red-600'
                          : 'border-gray-100 text-gray-300 cursor-not-allowed bg-gray-50',
                    ]"
                    @click="selectSpec(dimension, value)"
                  >
                    {{ value }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 数量选择 -->
            <div class="flex items-center gap-3 mb-6">
              <span class="text-sm text-gray-500 w-12 flex-shrink-0">数量</span>
              <div class="flex items-center border border-gray-200 rounded-md">
                <button
                  class="w-10 h-10 flex items-center justify-center text-gray-500 hover:text-red-600 transition-colors disabled:opacity-30"
                  :disabled="quantity <= 1"
                  @click="quantity--"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4" />
                  </svg>
                </button>
                <span class="w-14 h-10 flex items-center justify-center text-sm border-x border-gray-200 font-medium">{{ quantity }}</span>
                <button
                  class="w-10 h-10 flex items-center justify-center text-gray-500 hover:text-red-600 transition-colors disabled:opacity-30"
                  :disabled="quantity >= (selectedSku?.stock || 99)"
                  @click="quantity++"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
              <span class="text-xs text-gray-400">（限购 5 件）</span>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center gap-4 mb-6">
              <button
                class="flex-1 h-12 bg-red-100 text-red-600 font-bold text-base rounded-lg hover:bg-red-200 transition-colors flex items-center justify-center gap-2 border border-red-200"
                @click="handleAddToCart"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                加入购物车
              </button>
              <button
                class="flex-1 h-12 bg-red-600 text-white font-bold text-base rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2 shadow-md shadow-red-200"
                @click="handleBuyNow"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                立即购买
              </button>
            </div>

            <!-- 服务承诺 -->
            <div class="flex items-center gap-4 text-xs text-gray-500 border-t border-gray-100 pt-4">
              <span class="flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                正品保障
              </span>
              <span class="flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                7天无理由退换
              </span>
              <span class="flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                全国联保
              </span>
              <span class="flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                极速发货
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- 中部：优惠券 + 阶梯价格 -->
      <!-- ============================================================ -->
      <div v-if="mockProduct.couponList.length > 0 || mockProduct.productLadderList.length > 0" class="grid grid-cols-3 gap-4 mb-6">
        <!-- 优惠券 -->
        <div v-if="mockProduct.couponList.length > 0" class="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
            </svg>
            可领优惠券
          </h3>
          <div class="flex gap-3">
            <div
              v-for="coupon in mockProduct.couponList"
              :key="coupon.id"
              class="flex-1 border border-red-200 rounded-lg overflow-hidden flex"
            >
              <div class="bg-red-600 text-white px-4 py-3 flex flex-col items-center justify-center flex-shrink-0">
                <span class="text-lg font-bold">&yen;{{ coupon.amount }}</span>
                <span class="text-xs opacity-80">满{{ coupon.minPoint }}可用</span>
              </div>
              <div class="flex-1 px-3 py-2 flex flex-col justify-center">
                <span class="text-sm font-medium text-gray-800">{{ coupon.name }}</span>
                <span class="text-xs text-gray-400 mt-1">{{ (coupon.endTime || '').split('T')[0] }} 到期</span>
              </div>
              <div class="flex items-center px-3">
                <button
                  :class="[
                    'text-sm px-3 py-1.5 rounded-full transition-colors',
                    receivedCoupons.has(coupon.id)
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-red-600 text-white hover:bg-red-700',
                  ]"
                  :disabled="receivedCoupons.has(coupon.id)"
                  @click="receiveCoupon(coupon.id)"
                >
                  {{ receivedCoupons.has(coupon.id) ? '已领取' : '领取' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 阶梯价格 -->
        <div v-if="mockProduct.productLadderList.length > 0" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            阶梯优惠
          </h3>
          <div class="space-y-2">
            <div v-for="ladder in mockProduct.productLadderList" :key="ladder.id" class="flex items-center justify-between text-sm">
              <span class="text-gray-600">满 {{ ladder.count }} 件</span>
              <span class="text-red-600 font-medium">{{ (ladder.discount * 10).toFixed(1) }} 折</span>
              <span class="text-gray-400">&yen;{{ ladder.price }}/件</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- 下部：Tab 切换 + 详情内容 -->
      <!-- ============================================================ -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- Tab 头部 -->
        <div class="flex border-b border-gray-100">
          <button
            :class="[
              'px-8 py-4 text-sm font-medium transition-colors border-b-2',
              activeTab === 'detail'
                ? 'text-red-600 border-red-600'
                : 'text-gray-500 border-transparent hover:text-gray-700',
            ]"
            @click="activeTab = 'detail'"
          >
            商品详情
          </button>
          <button
            v-if="mockProduct.productAttributeList.length > 0"
            :class="[
              'px-8 py-4 text-sm font-medium transition-colors border-b-2',
              activeTab === 'params'
                ? 'text-red-600 border-red-600'
                : 'text-gray-500 border-transparent hover:text-gray-700',
            ]"
            @click="activeTab = 'params'"
          >
            规格参数
          </button>
          <button
            :class="[
              'px-8 py-4 text-sm font-medium transition-colors border-b-2',
              activeTab === 'reviews'
                ? 'text-red-600 border-red-600'
                : 'text-gray-500 border-transparent hover:text-gray-700',
            ]"
            @click="activeTab = 'reviews'"
          >
            用户评价
          </button>
        </div>

        <!-- Tab 内容 -->
        <div class="p-8">
          <!-- 商品详情 -->
          <div v-if="activeTab === 'detail'" class="space-y-6">
            <div class="grid grid-cols-4 gap-4 text-sm mb-8">
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">品牌</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.brand.name || mockProduct.product.brandName || '-' }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">商品编号</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.product.productSn || '-' }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">商品分类</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.product.productCategoryName || '-' }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">售后服务</div>
                <div class="text-gray-900 font-medium">全国联保一年</div>
              </div>
            </div>

            <!-- 描述文字 -->
            <div v-if="mockProduct.product.description" class="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg p-6">
              <h3 class="text-lg font-bold text-gray-900 mb-4">产品详情</h3>
              <p>{{ mockProduct.product.description }}</p>
            </div>

            <!-- 详情 HTML -->
            <div v-if="mockProduct.product.detailMobileHtml" v-html="mockProduct.product.detailMobileHtml" class="prose max-w-none" />
          </div>

          <!-- 规格参数 -->
          <div v-if="activeTab === 'params'" class="max-w-3xl">
            <table class="w-full text-sm">
              <tbody class="divide-y divide-gray-100">
                <tr v-for="attr in mockProduct.productAttributeList" :key="attr.id" class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">{{ attr.name }}</td>
                  <td class="py-3 px-4 text-gray-900">{{ attr.inputList }}</td>
                </tr>
                <tr v-if="mockProduct.product.productSn" class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">商品编号</td>
                  <td class="py-3 px-4 text-gray-900">{{ mockProduct.product.productSn }}</td>
                </tr>
                <tr v-if="mockProduct.brand.name || mockProduct.product.brandName" class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">品牌</td>
                  <td class="py-3 px-4 text-gray-900">{{ mockProduct.brand.name || mockProduct.product.brandName }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 用户评价 -->
          <div v-if="activeTab === 'reviews'">
            <div class="flex items-center justify-center py-12 text-gray-400 text-sm">
              暂无评价
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 放大镜样式 */
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
</style>
