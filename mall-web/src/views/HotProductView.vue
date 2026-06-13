<script setup lang="ts">
/**
 * ============================================
 * 热门推荐页 (HotProductView)
 * 营销聚合页：顶部 Banner 氛围图 + 热销排行网格
 * ============================================
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { PmsProduct } from '@/types/product'

const router = useRouter()

/** Mock 热销数据 */
const products = ref<PmsProduct[]>([
  { id: 101, name: 'Apple MacBook Air M3芯片 16GB+512GB', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', price: 9999, originalPrice: 11999, sale: 12580, brandId: 1, brandName: 'Apple', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: 'M3芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 1, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 102, name: '戴森 Dyson HD15 新一代吹风机 负离子护发', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', price: 2590, originalPrice: 3290, sale: 8900, brandId: 7, brandName: 'Dyson', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '智能温控', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 2, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 103, name: 'SK-II 神仙水护肤精华露 230ml', pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=300&h=300&fit=crop', price: 1540, originalPrice: 2150, sale: 2900, brandId: 14, brandName: 'SK-II', productCategoryId: 6, productCategoryName: '美妆个护', subTitle: 'PITERA精华', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 3, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 104, name: 'Nike Air Force 1 经典板鞋男女同款', pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop', price: 749, originalPrice: 899, sale: 6100, brandId: 4, brandName: 'Nike', productCategoryId: 5, productCategoryName: '服装服饰', subTitle: '经典百搭', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 4, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 105, name: '小米14 Pro 16GB+512GB 徕卡影像', pic: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop', price: 5499, originalPrice: 5999, sale: 4500, brandId: 3, brandName: '小米', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '骁龙8 Gen3', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 5, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 106, name: '雅诗兰黛 小棕瓶精华液 50ml 修护抗老', pic: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=300&h=300&fit=crop', price: 935, originalPrice: 1280, sale: 2100, brandId: 17, brandName: '雅诗兰黛', productCategoryId: 6, productCategoryName: '美妆个护', subTitle: '第七代', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 6, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 107, name: '索尼 Sony PS5 光驱版游戏主机 国行', pic: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=300&h=300&fit=crop', price: 3599, originalPrice: 3899, sale: 1800, brandId: 6, brandName: 'Sony', productCategoryId: 7, productCategoryName: '运动户外', subTitle: '4K 120Hz', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 7, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 108, name: 'Nespresso 胶囊咖啡机 Essenza Mini', pic: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=300&h=300&fit=crop', price: 866, originalPrice: 1280, sale: 1500, brandId: 19, brandName: 'Nespresso', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '全自动', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 8, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
])

const formatPrice = (p: number) => p.toLocaleString('zh-CN')
</script>

<template>
  <div class="hot-product-page">
    <!-- ====== Banner 氛围图 ====== -->
    <div class="relative rounded-xl overflow-hidden mb-6 h-[160px]">
      <img src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=300&fit=crop" alt="热门推荐" class="w-full h-full object-cover" />
      <div class="absolute inset-0 bg-gradient-to-r from-orange-600/80 to-red-500/60" />
      <div class="absolute inset-0 flex items-center px-10">
        <div>
          <h1 class="text-3xl font-bold text-white mb-2">热门推荐</h1>
          <p class="text-white/80 text-sm">精选好物，品质保障，万人之选</p>
        </div>
        <div class="ml-auto text-white text-center">
          <div class="text-2xl font-bold">{{ products.length }}</div>
          <div class="text-xs opacity-70">款热销</div>
        </div>
      </div>
    </div>

    <!-- ====== 热销排行网格 ====== -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="(product, index) in products"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden relative"
        @click="router.push(`/product/${product.id}`)"
      >
        <!-- 排行角标 -->
        <div
          :class="[
            'absolute top-2 left-2 z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white',
            index === 0 ? 'bg-red-600' : index === 1 ? 'bg-orange-500' : index === 2 ? 'bg-yellow-500' : 'bg-gray-400',
          ]"
        >
          {{ index + 1 }}
        </div>

        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.pic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
        </div>
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ formatPrice(product.price) }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ formatPrice(product.originalPrice) }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-orange-500 font-medium">已售 {{ product.sale >= 10000 ? (product.sale / 10000).toFixed(1) + '万' : product.sale }}</span>
            <span class="text-xs text-gray-400">{{ product.brandName }}</span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
