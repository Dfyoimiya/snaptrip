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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { addCartAPI } from '@/apis/cart'
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
// Mock 数据：商品详情
// ============================================================

interface MockProductDetail {
  product: {
    id: number
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
  productAttributeList: { id: number; name: string; type: number; inputList: string }[]
  productAttributeValueList: { id: number; productAttributeId: number; value: string }[]
  productFullReductionList: { id: number; fullPrice: number; reducePrice: number }[]
  productLadderList: { id: number; count: number; discount: number; price: number }[]
  couponList: SmsCoupon[]
}

const productImages = [
  'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&h=800&fit=crop',
  'https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=800&h=800&fit=crop',
  'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&h=800&fit=crop',
  'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800&h=800&fit=crop',
  'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&h=800&fit=crop',
]

const mockProduct = ref<MockProductDetail>({
  product: {
    id: 101,
    name: 'Apple MacBook Air 13.6英寸 M3芯片 8核CPU 10核GPU 16GB+512GB',
    subTitle: '【教育优惠】苹果官方授权 | 12期免息 | 全国联保一年 | 轻薄便携 超长续航',
    price: 10499,
    originalPrice: 11999,
    sale: 12580,
    stock: 368,
    brandName: 'Apple',
    productCategoryName: '笔记本电脑',
    pic: productImages[0],
    albumPics: productImages.join(','),
    description: '全新 MacBook Air 搭载 Apple M3 芯片，带来超凡性能和长达 18 小时的电池续航。轻薄设计，Liquid 视网膜显示屏，让每一天的工作和创造都轻松自如。',
    serviceIds: '1,2,3',
    productSn: 'APPLE-MBA-M3-2024',
    promotionType: 1,
    detailMobileHtml: '',
  },
  brand: {
    id: 1,
    name: 'Apple',
    firstLetter: 'A',
    logo: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=80&h=80&fit=crop',
    bigPic: '',
    brandStory: 'Apple 是全球领先的科技公司，以创新设计和卓越用户体验闻名。',
    sort: 1,
    showStatus: 1,
    productCount: 156,
    productCommentCount: 89000,
    pic: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=80&h=80&fit=crop',
    createTime: '2024-01-01',
  },
  skuStockList: [
    { id: 1001, skuCode: '午夜色 M3-8C-16G-256G', price: 8999, stock: 120, promotionPrice: 8499, spData: '{"颜色":"午夜色","芯片":"M3","内存":"16GB","硬盘":"256GB"}', lockStock: 5, lowStock: 10, pic: productImages[0], productId: 101, sale: 3200 },
    { id: 1002, skuCode: '星光色 M3-8C-16G-256G', price: 8999, stock: 85, promotionPrice: 8499, spData: '{"颜色":"星光色","芯片":"M3","内存":"16GB","硬盘":"256GB"}', lockStock: 3, lowStock: 10, pic: productImages[1], productId: 101, sale: 2100 },
    { id: 1003, skuCode: '午夜色 M3-10C-16G-512G', price: 10499, stock: 68, promotionPrice: 9999, spData: '{"颜色":"午夜色","芯片":"M3","内存":"16GB","硬盘":"512GB"}', lockStock: 8, lowStock: 10, pic: productImages[2], productId: 101, sale: 2800 },
    { id: 1004, skuCode: '星光色 M3-10C-16G-512G', price: 10499, stock: 45, promotionPrice: 9999, spData: '{"颜色":"星光色","芯片":"M3","内存":"16GB","硬盘":"512GB"}', lockStock: 4, lowStock: 10, pic: productImages[3], productId: 101, sale: 1900 },
    { id: 1005, skuCode: '银色 M3-10C-24G-512G', price: 12499, stock: 30, promotionPrice: 11899, spData: '{"颜色":"银色","芯片":"M3","内存":"24GB","硬盘":"512GB"}', lockStock: 2, lowStock: 5, pic: productImages[4], productId: 101, sale: 1580 },
  ],
  productAttributeList: [
    { id: 1, name: '颜色', type: 0, inputList: '午夜色,星光色,银色' },
    { id: 2, name: '芯片', type: 0, inputList: 'M3-8C,M3-10C' },
    { id: 3, name: '内存', type: 0, inputList: '16GB,24GB' },
  ],
  productAttributeValueList: [
    { id: 1, productAttributeId: 1, value: '午夜色' },
    { id: 2, productAttributeId: 2, value: 'M3-10C' },
    { id: 3, productAttributeId: 3, value: '16GB' },
  ],
  productFullReductionList: [
    { id: 1, fullPrice: 10000, reducePrice: 500 },
    { id: 2, fullPrice: 8000, reducePrice: 200 },
  ],
  productLadderList: [
    { id: 1, count: 2, discount: 0.98, price: 10289 },
    { id: 2, count: 5, discount: 0.95, price: 9974 },
  ],
  couponList: [
    { id: 1, type: 0, name: '新客专享券', platform: 2, count: 100, amount: 200, perLimit: 1, minPoint: 8000, startTime: '2026-06-01T00:00:00', endTime: '2026-06-30T23:59:59', useType: 0, code: 'NEW200', memberLevel: 0, publishCount: 100, receiveCount: 45, useCount: 12, receiveTime: '', enableTime: '', createTime: '' },
    { id: 2, type: 1, name: '数码品类券', platform: 2, count: 50, amount: 500, perLimit: 1, minPoint: 10000, startTime: '2026-06-01T00:00:00', endTime: '2026-06-15T23:59:59', useType: 0, code: 'DIG500', memberLevel: 0, publishCount: 50, receiveCount: 28, useCount: 8, receiveTime: '', enableTime: '', createTime: '' },
  ],
})

// ============================================================
// 状态管理
// ============================================================

/** 加载状态 */
const loading = ref(false)
/** 当前选中的 SKU */
const selectedSku = ref<PmsSkuStock>(mockProduct.value.skuStockList[2])
/** 购买数量 */
const quantity = ref(1)
/** 当前主图索引 */
const currentImageIndex = ref(0)
/** 详情 Tab 选中 */
const activeTab = ref<'detail' | 'params' | 'reviews'>('detail')

/** 计算当前显示的主图 */
const currentMainImage = computed(() => {
  // 优先使用 SKU 对应的图片
  const skuImage = selectedSku.value?.pic
  if (skuImage && currentImageIndex.value === 0) {
    return skuImage
  }
  return productImages[currentImageIndex.value]
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

// 初始化选中规格
const initSelectedSpecs = () => {
  const first = parsedSkuSpecs.value[0]
  if (first) {
    selectedSpecs.value = { ...first.specs }
  }
}
initSelectedSpecs()

/** 判断某个规格值是否被选中 */
const isSpecSelected = (dimension: string, value: string) => {
  return selectedSpecs.value[dimension] === value
}

/** 选择规格值 */
const selectSpec = (dimension: string, value: string) => {
  selectedSpecs.value[dimension] = value
  // 联动：找到匹配的 SKU
  const matched = parsedSkuSpecs.value.find(({ specs }) => {
    return specDimensions.value.every(
      (dim) => selectedSpecs.value[dim] === specs[dim]
    )
  })
  if (matched) {
    selectedSku.value = matched.sku
  }
}

/** 判断某规格值是否存在对应 SKU */
const isSpecAvailable = (dimension: string, value: string) => {
  // 检查是否存在包含该规格值的 SKU（且库存>0）
  return parsedSkuSpecs.value.some(({ sku, specs }) => {
    if (sku.stock <= 0) return false
    // 当前维度匹配该值，其他维度保持已选值
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

  // 限制在图片范围内
  if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
    showMagnifier.value = false
    return
  }

  showMagnifier.value = true
  magnifierPosition.value = { x, y }

  // 更新放大镜背景位置
  if (magnifierRef.value) {
    const lensSize = 120 // 放大镜镜头大小
    const bgX = (x / rect.width) * 100
    const bgY = (y / rect.height) * 100
    magnifierRef.value.style.backgroundPosition = `${bgX}% ${bgY}%`
    magnifierRef.value.style.backgroundSize = `${rect.width * zoomLevel}px ${rect.height * zoomLevel}px`

    // 镜头跟随鼠标
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

/** 添加到购物车 */
const handleAddToCart = async () => {
  if (!selectedSku.value) return
  try {
    await addCartAPI({
      productId: mockProduct.value.product.id,
      productSkuId: selectedSku.value.id,
      quantity: quantity.value,
    })
    await cartStore.fetchCartList()
    // 简单的成功提示
    const toast = document.createElement('div')
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm font-medium animate-fade-in'
    toast.textContent = '已成功添加到购物车'
    document.body.appendChild(toast)
    setTimeout(() => toast.remove(), 2000)
  } catch {
    // 降级：本地提示
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
    router.push(`/login?redirect=/product/${mockProduct.value.product.id}`)
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
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 300)
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
      <button class="hover:text-red-600 transition-colors" @click="router.push('/category')">{{ mockProduct.product.productCategoryName }}</button>
      <span class="text-gray-300">/</span>
      <button class="hover:text-red-600 transition-colors" @click="router.push(`/brand/${mockProduct.brand.id}`)">{{ mockProduct.product.brandName }}</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-700 truncate max-w-md">{{ mockProduct.product.name }}</span>
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
            <div class="flex gap-2">
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
            <p class="text-sm text-red-600 mb-4 leading-5">
              {{ mockProduct.product.subTitle }}
            </p>

            <!-- 价格区 -->
            <div class="bg-gray-50 rounded-lg p-4 mb-5">
              <div class="flex items-baseline gap-3 mb-2">
                <span class="text-sm text-gray-500">促销价</span>
                <span class="text-3xl font-bold text-red-600">
                  <span class="text-lg">&yen;</span>{{ formatPrice(selectedSku?.promotionPrice || selectedSku?.price || mockProduct.product.price) }}
                </span>
                <span class="text-sm text-gray-400 line-through">
                  &yen;{{ formatPrice(selectedSku?.price || mockProduct.product.originalPrice) }}
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
                <div class="flex items-center gap-2 text-sm">
                  <span class="bg-orange-500 text-white text-xs px-2 py-0.5 rounded">分期</span>
                  <span class="text-gray-600">12期免息，月供低至 &yen;{{ Math.round((selectedSku?.promotionPrice || selectedSku?.price || 0) / 12) }}</span>
                </div>
              </div>
            </div>

            <!-- SKU 规格选择 -->
            <div class="mb-5 space-y-4">
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
                  <path stroke-linecap="round" stroke-linejoin="round"join="round" d="M5 13l4 4L19 7" />
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
      <div class="grid grid-cols-3 gap-4 mb-6">
        <!-- 优惠券 -->
        <div class="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
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
                <span class="text-xs text-gray-400 mt-1">{{ coupon.endTime.split('T')[0] }} 到期</span>
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
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
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
            用户评价 (1.2万+)
          </button>
        </div>

        <!-- Tab 内容 -->
        <div class="p-8">
          <!-- 商品详情 -->
          <div v-if="activeTab === 'detail'" class="space-y-6">
            <div class="grid grid-cols-4 gap-4 text-sm mb-8">
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">品牌</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.brand.name }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">商品编号</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.product.productSn }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">商品分类</div>
                <div class="text-gray-900 font-medium">{{ mockProduct.product.productCategoryName }}</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <div class="text-gray-400 mb-1">售后服务</div>
                <div class="text-gray-900 font-medium">全国联保一年</div>
              </div>
            </div>

            <!-- 详情长图 -->
            <div class="text-center">
              <h3 class="text-lg font-bold text-gray-900 mb-6">产品详情</h3>
              <div class="space-y-4">
                <img
                  src="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&h=600&fit=crop"
                  alt="产品详情1"
                  class="w-full rounded-lg"
                />
                <img
                  src="https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=1200&h=600&fit=crop"
                  alt="产品详情2"
                  class="w-full rounded-lg"
                />
                <img
                  src="https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&h=600&fit=crop"
                  alt="产品详情3"
                  class="w-full rounded-lg"
                />
                <img
                  src="https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200&h=600&fit=crop"
                  alt="产品详情4"
                  class="w-full rounded-lg"
                />
              </div>
            </div>
          </div>

          <!-- 规格参数 -->
          <div v-if="activeTab === 'params'" class="max-w-3xl">
            <table class="w-full text-sm">
              <tbody class="divide-y divide-gray-100">
                <tr v-for="attr in mockProduct.productAttributeList" :key="attr.id" class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">{{ attr.name }}</td>
                  <td class="py-3 px-4 text-gray-900">{{ attr.inputList }}</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">商品编号</td>
                  <td class="py-3 px-4 text-gray-900">{{ mockProduct.product.productSn }}</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">品牌</td>
                  <td class="py-3 px-4 text-gray-900">{{ mockProduct.brand.name }}</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">屏幕尺寸</td>
                  <td class="py-3 px-4 text-gray-900">13.6 英寸</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">分辨率</td>
                  <td class="py-3 px-4 text-gray-900">2560 x 1664</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">处理器</td>
                  <td class="py-3 px-4 text-gray-900">Apple M3 芯片（8 核中央处理器，10 核图形处理器）</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">电池续航</td>
                  <td class="py-3 px-4 text-gray-900">最长可达 18 小时</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">重量</td>
                  <td class="py-3 px-4 text-gray-900">1.24 千克</td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="py-3 px-4 text-gray-500 w-32 bg-gray-50">接口</td>
                  <td class="py-3 px-4 text-gray-900">MagSafe 3 充电端口、2 个雷雳 / USB 4 端口、3.5 毫米耳机插孔</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 用户评价 -->
          <div v-if="activeTab === 'reviews'">
            <div class="flex items-center gap-8 mb-6">
              <div class="text-center">
                <div class="text-4xl font-bold text-red-600">4.9</div>
                <div class="text-sm text-gray-500 mt-1">综合评分</div>
              </div>
              <div class="flex-1 space-y-1">
                <div v-for="star in [5, 4, 3, 2, 1]" :key="star" class="flex items-center gap-2 text-sm">
                  <span class="text-gray-500 w-8">{{ star }}星</span>
                  <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-red-500 rounded-full"
                      :style="{ width: star === 5 ? '92%' : star === 4 ? '6%' : star === 3 ? '1.5%' : '0.5%' }"
                    />
                  </div>
                  <span class="text-gray-400 w-12 text-right">{{ star === 5 ? '92%' : star === 4 ? '6%' : star === 3 ? '1.5%' : '0.5%' }}</span>
                </div>
              </div>
            </div>

            <!-- 评价列表 -->
            <div class="space-y-4 divide-y divide-gray-100">
              <div v-for="i in 3" :key="i" class="pt-4 first:pt-0">
                <div class="flex items-center gap-3 mb-2">
                  <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs text-gray-500">
                    {{ ['用', 'A', 'L'][i - 1] }}
                  </div>
                  <div>
                    <div class="text-sm text-gray-700">{{ ['用户9527', 'AppleFan2024', 'Lisa_Tech'][i - 1] }}</div>
                    <div class="flex items-center gap-1">
                      <svg v-for="s in 5" :key="s" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    </div>
                  </div>
                  <span class="ml-auto text-xs text-gray-400">2026-0{{ i + 3 }}-{{ 10 + i }}</span>
                </div>
                <p class="text-sm text-gray-700 leading-relaxed">
                  {{ [
                    '用了几天来评价，M3芯片性能真的很强，日常办公完全没问题，电池续航也很给力，一天用下来还有40%多。屏幕显示效果细腻，午夜色实物比图片更好看。',
                    '从Intel版本换过来的，提升非常明显。运行速度快了很多，发热也控制得很好。16GB内存对于多任务处理来说完全够用，512GB硬盘存储日常文件也够了。',
                    '给上大学的孩子买的，教育优惠省了900块。做工一如既往地精致，星光色很高级。物流很快，第二天就到了。'
                  ][i - 1] }}
                </p>
                <div class="flex items-center gap-2 mt-2 text-xs text-gray-400">
                  <span>购买规格：{{ ['午夜色 M3-10C-16G-512G', '星光色 M3-8C-16G-256G', '银色 M3-10C-24G-512G'][i - 1] }}</span>
                </div>
              </div>
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
