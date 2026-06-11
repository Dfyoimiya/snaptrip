<script setup lang="ts">
/**
 * ============================================
 * 品牌详情页 (BrandDetailView)
 * 品牌大图 Banner + 旗下商品列表 + 排序筛选
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { PmsProduct } from '@/types/product'

const route = useRoute()
const router = useRouter()

/** Mock 品牌数据 */
const brandMap: Record<number, { id: number; name: string; firstLetter: string; logo: string; banner: string; brandStory: string; productCount: number }> = {
  1: { id: 1, name: 'Apple', firstLetter: 'A', logo: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1491933382434-500287f9b54b?w=1200&h=300&fit=crop', brandStory: 'Apple 是全球领先的科技公司，以创新设计和卓越用户体验闻名。从 Macintosh 到 iPhone，Apple 始终致力于通过突破性技术改变世界。', productCount: 156 },
  2: { id: 2, name: '华为 HUAWEI', firstLetter: 'H', logo: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&h=300&fit=crop', brandStory: '华为是全球领先的ICT（信息与通信）基础设施和智能终端提供商，致力于把数字世界带入每个人、每个家庭、每个组织，构建万物互联的智能世界。', productCount: 328 },
  3: { id: 3, name: '小米 Xiaomi', firstLetter: 'X', logo: 'https://images.unsplash.com/photo-1567581935884-3349723552ca?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=1200&h=300&fit=crop', brandStory: '小米是一家以手机、智能硬件和IoT平台为核心的互联网公司，始终坚持做"感动人心、价格厚道"的好产品，让全球每个人都能享受科技带来的美好生活。', productCount: 512 },
  4: { id: 4, name: 'Nike', firstLetter: 'N', logo: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1200&h=300&fit=crop', brandStory: 'Nike 是全球著名的体育运动品牌，总部位于美国俄勒冈州。以其标志性的 Swoosh 商标和 "Just Do It" 口号闻名于世。', productCount: 892 },
  6: { id: 6, name: 'Sony', firstLetter: 'S', logo: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=1200&h=300&fit=crop', brandStory: 'Sony 是日本一家全球知名的大型综合性跨国企业集团，是世界视听、电子游戏、通讯产品和信息技术等领域的先导者。', productCount: 198 },
  7: { id: 7, name: 'Dyson', firstLetter: 'D', logo: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=1200&h=300&fit=crop', brandStory: 'Dyson 是一家英国技术创新公司，以设计和制造吸尘器、吹风机、空气净化器等家电产品而闻名，致力于用科技解决日常问题。', productCount: 45 },
  8: { id: 8, name: '三星 SAMSUNG', firstLetter: 'S', logo: 'https://images.unsplash.com/photo-1610945265064-f4d215f72119?w=200&h=200&fit=crop', banner: 'https://images.unsplash.com/photo-1610945265064-f4d215f72119?w=1200&h=300&fit=crop', brandStory: '三星是韩国最大的跨国企业集团，业务涵盖电子、金融、机械、化学等众多领域，是全球消费电子市场的领导者。', productCount: 267 },
}

/** 当前品牌 */
const brandId = Number(route.params.id)
const brand = computed(() => brandMap[brandId] || brandMap[1])

/** 排序方式 */
const sortType = ref(0)
const sortOptions = [
  { label: '综合排序', value: 0 },
  { label: '销量', value: 2 },
  { label: '价格从低到高', value: 3 },
  { label: '价格从高到低', value: 4 },
  { label: '新品', value: 1 },
]

/** 当前页 */
const currentPage = ref(1)
const pageSize = 12

/** Mock 商品列表 */
const brandProducts = ref<PmsProduct[]>([
  { id: 1, name: 'Apple iPhone 15 Pro Max 256GB 钛金属', pic: 'https://images.unsplash.com/photo-1696446701796-da61225697cc?w=300&h=300&fit=crop', price: 9999, originalPrice: 10999, sale: 5200, stock: 200, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'A17 Pro芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 1, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 4, name: 'Apple MacBook Air M3 16GB+512GB', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', price: 10499, originalPrice: 11999, sale: 3200, stock: 80, brandId: 1, brandName: 'Apple', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: 'M3芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 4, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 13, name: 'Apple Watch Series 9 GPS版 45mm', pic: 'https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=300&h=300&fit=crop', price: 2999, originalPrice: 3499, sale: 4200, stock: 150, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'S9 SiP', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 13, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 19, name: 'AirPods Pro 2 USB-C版 主动降噪', pic: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=300&h=300&fit=crop', price: 1899, originalPrice: 2199, sale: 18000, stock: 400, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'H2芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 19, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 101, name: 'Apple iPad Pro 12.9英寸 M2芯片 WiFi版', pic: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=300&h=300&fit=crop', price: 8499, originalPrice: 9299, sale: 2100, stock: 65, brandId: 1, brandName: 'Apple', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: 'M2芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 101, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 102, name: 'Apple HomePod mini 智能音响 白色', pic: 'https://images.unsplash.com/photo-1545454675-3531b543be5d?w=300&h=300&fit=crop', price: 749, originalPrice: 849, sale: 5600, stock: 120, brandId: 1, brandName: 'Apple', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '360度音频', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 102, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 103, name: 'Apple TV 4K 2023款 128GB', pic: 'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=300&h=300&fit=crop', price: 1499, originalPrice: 1699, sale: 890, stock: 45, brandId: 1, brandName: 'Apple', productCategoryId: 3, productCategoryName: '家用电器', subTitle: 'A15仿生', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 103, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 104, name: 'Apple MagSafe 外接电池 无线充电宝', pic: 'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=300&h=300&fit=crop', price: 749, originalPrice: 899, sale: 3200, stock: 200, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '磁吸充电', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 104, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
])

/** 排序后的商品 */
const sortedProducts = computed(() => {
  const result = [...brandProducts.value]
  if (sortType.value === 2) result.sort((a, b) => b.sale - a.sale)
  else if (sortType.value === 3) result.sort((a, b) => a.price - b.price)
  else if (sortType.value === 4) result.sort((a, b) => b.price - a.price)
  else if (sortType.value === 1) result.sort((a, b) => b.newStatus - a.newStatus)
  return result
})

const totalPages = computed(() => Math.ceil(sortedProducts.value.length / pageSize))
const paginatedProducts = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return sortedProducts.value.slice(start, start + pageSize)
})

const goPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

const goProductDetail = (id: number) => router.push(`/product/${id}`)
</script>

<template>
  <div class="brand-detail-page space-y-5">
    <!-- ====== 品牌 Banner ====== -->
    <div class="relative rounded-xl overflow-hidden h-[200px]">
      <img :src="brand.banner" :alt="brand.name" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent" />
      <div class="absolute inset-0 flex items-center px-8">
        <div class="flex items-center gap-5">
          <div class="w-20 h-20 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center overflow-hidden">
            <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-white">{{ brand.name }}</h1>
            <p class="text-sm text-white/70 mt-1 max-w-lg">{{ brand.brandStory }}</p>
            <p class="text-xs text-white/50 mt-2">{{ brand.productCount }} 件商品在售</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 商品筛选排序 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1">
          <button
            v-for="opt in sortOptions"
            :key="opt.value"
            :class="[
              'px-4 py-2 text-sm rounded-md transition-colors',
              sortType === opt.value ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100',
            ]"
            @click="sortType = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
        <span class="text-sm text-gray-400">共 {{ brandProducts.length }} 件商品</span>
      </div>
    </div>

    <!-- ====== 商品网格 ====== -->
    <div v-if="paginatedProducts.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in paginatedProducts"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="goProductDetail(product.id)"
      >
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.pic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <span v-if="product.originalPrice > product.price" class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
            省{{ Math.round((1 - product.price / product.originalPrice) * 100) }}%
          </span>
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ product.price }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ product.originalPrice }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400">已售 {{ product.sale >= 10000 ? (product.sale / 10000).toFixed(1) + '万' : product.sale }}</span>
            <span class="text-xs text-gray-400">{{ product.subTitle }}</span>
          </div>
        </div>
      </button>
    </div>

    <!-- ====== 分页器 ====== -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-4">
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
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
        :class="['min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors', currentPage === page ? 'bg-red-600 text-white font-medium' : 'border border-gray-200 text-gray-600 hover:bg-gray-50']"
        @click="goPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
        :disabled="currentPage === totalPages"
        @click="goPage(currentPage + 1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
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
