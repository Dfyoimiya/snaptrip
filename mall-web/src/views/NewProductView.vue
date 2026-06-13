<script setup lang="ts">
/**
 * ============================================
 * 新品首发页 (NewProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 新品商品网格
 * ============================================
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { PmsProduct } from '@/types/product'

const router = useRouter()

/** Mock 新品数据 */
const products = ref<PmsProduct[]>([
  { id: 201, name: '华为 Mate 60 Pro+ 16GB+512GB 鸿蒙系统 卫星通信', pic: 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=300&h=300&fit=crop', price: 8999, originalPrice: 9999, sale: 320, brandId: 2, brandName: '华为', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '麒麟9000S', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 1, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-08', updateTime: '' },
  { id: 202, name: 'DJI Osmo Pocket 3 口袋云台相机 4K 120fps', pic: 'https://images.unsplash.com/photo-1564466021188-1e17010c5352?w=300&h=300&fit=crop', price: 3499, originalPrice: 3999, sale: 180, brandId: 20, brandName: 'DJI', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '一英寸云台', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 2, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-07', updateTime: '' },
  { id: 203, name: '科沃斯 ECOVACS X2 Pro 扫地机器人 自动上下水', pic: 'https://images.unsplash.com/photo-1588854337221-4cf9fa96059c?w=300&h=300&fit=crop', price: 4999, originalPrice: 6499, sale: 260, brandId: 10, brandName: '科沃斯', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '方形旗舰', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 3, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-06', updateTime: '' },
  { id: 204, name: 'Lululemon Align 女士运动瑜伽裤 高腰裸感', pic: 'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=300&h=300&fit=crop', price: 850, originalPrice: 1080, sale: 410, brandId: 18, brandName: 'Lululemon', productCategoryId: 5, productCategoryName: '服装服饰', subTitle: 'Nulu面料', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 4, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-05', updateTime: '' },
  { id: 205, name: 'Anker 737 240W 氮化镓充电器 三口快充', pic: 'https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=300&h=300&fit=crop', price: 399, originalPrice: 599, sale: 580, brandId: 15, brandName: 'Anker', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'GaNPrime', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 5, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-04', updateTime: '' },
  { id: 206, name: 'Philips 飞利浦 Sonicare 钻石牙刷 HX9912', pic: 'https://images.unsplash.com/photo-1559671088-795c52083351?w=300&h=300&fit=crop', price: 1299, originalPrice: 1899, sale: 230, brandId: 19, brandName: 'Philips', productCategoryId: 6, productCategoryName: '美妆个护', subTitle: '智能传感', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 6, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-03', updateTime: '' },
  { id: 207, name: 'Bose QuietComfort Ultra 无线消噪耳机', pic: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop', price: 2299, originalPrice: 2999, sale: 170, brandId: 15, brandName: 'Bose', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '沉浸音频', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 7, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-02', updateTime: '' },
  { id: 208, name: '戴森 Dyson Airwrap 多功能造型器 长发版', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', price: 3999, originalPrice: 4590, sale: 120, brandId: 7, brandName: 'Dyson', productCategoryId: 6, productCategoryName: '美妆个护', subTitle: '气流造型', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 8, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '2026-06-01', updateTime: '' },
])

const formatPrice = (p: number) => p.toLocaleString('zh-CN')
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

    <!-- ====== 新品商品网格 ====== -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in products"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="router.push(`/product/${product.id}`)"
      >
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.pic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <span class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded-full font-medium">NEW</span>
          <span v-if="product.originalPrice > product.price" class="absolute top-2 right-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
            省{{ Math.round((1 - product.price / product.originalPrice) * 100) }}%
          </span>
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-green-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ formatPrice(product.price) }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ formatPrice(product.originalPrice) }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400">已售 {{ product.sale }}</span>
            <span class="text-xs text-gray-400">{{ product.brandName }}</span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
