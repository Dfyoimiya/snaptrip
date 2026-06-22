<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getHomeContentAPI, getHomeFeedAPI } from '@/apis/home'
import type { FeedSection } from '@/apis/home'
import type { HomeContentResult } from '@/types/home'
import type { PmsProduct } from '@/types/product'
import ProductCard from '@/components/product/ProductCard.vue'

const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const homeContent = ref<HomeContentResult>({
  banners: [],
  newProducts: [],
  recommendProducts: [],
  subjects: [],
})
const feedSections = ref<FeedSection[]>([])

/** 合并所有商品，去重后直接平铺 */
const allProducts = computed<PmsProduct[]>(() => {
  const seen = new Set<string | number>()
  const products: PmsProduct[] = []

  for (const section of feedSections.value) {
    for (const item of section.products) {
      if (seen.has(item.productId)) continue
      seen.add(item.productId)
      products.push({
        id: item.productId,
        name: item.name,
        price: item.price,
        promotionPrice: item.promotionPrice,
        promotionType: item.promotionType,
        stock: item.stock,
        saleCount: item.saleCount,
        defaultPic: item.imageUrl,
        brandName: item.brandName,
        categoryId: item.categoryId,
        newStatus: item.newStatus,
        recommendStatus: item.recommendStatus,
        subTitle: item.marketingCopy,
      })
    }
  }

  for (const product of homeContent.value.recommendProducts) {
    if (seen.has(product.id)) continue
    seen.add(product.id)
    products.push(product)
  }
  for (const product of homeContent.value.newProducts) {
    if (seen.has(product.id)) continue
    seen.add(product.id)
    products.push(product)
  }

  return products
})

async function loadHome(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const [content] = await Promise.all([
      getHomeContentAPI(),
    ])
    homeContent.value = content
    void loadFeed()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '首页加载失败'
  } finally {
    loading.value = false
  }
}

async function loadFeed(): Promise<void> {
  try {
    const feed = await getHomeFeedAPI(24)
    feedSections.value = feed.sections
  } catch {
    feedSections.value = []
  }
}

onMounted(loadHome)
</script>

<template>
  <div class="home-page">
    <div v-if="loading" class="home-loading">
      <div v-for="index in 12" :key="index" class="skeleton-card" />
    </div>

    <div v-else-if="loadError" class="load-error">
      <strong>首页暂时走丢了</strong>
      <span>{{ loadError }}</span>
      <button @click="loadHome">重新加载</button>
    </div>

    <template v-else>
      <div class="product-grid">
        <ProductCard
          v-for="product in allProducts"
          :key="product.id"
          :product="product"
          :show-new-badge="product.newStatus === 1"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.home-page {
  /* 无容器 — 内容直接铺在底层灰白纸上 */
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}

.home-loading {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}

.skeleton-card {
  aspect-ratio: 1;
  border-radius: 12px;
  background: linear-gradient(90deg, #eee, #f5f5f5, #eee);
  background-size: 200% 100%;
  animation: pulse 1.3s infinite;
}

.load-error {
  min-height: 360px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: #999;
}
.load-error strong { color: #333; font-size: 20px; }
.load-error button {
  margin-top: 8px;
  border-radius: 999px;
  background: #ff5000;
  color: #fff;
  padding: 8px 22px;
}

@keyframes pulse { to { background-position: -200% 0; } }

@media (max-width: 1600px) {
  .product-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .home-loading { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
@media (max-width: 1400px) {
  .product-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .home-loading { grid-template-columns: repeat(5, minmax(0, 1fr)); }
}
@media (max-width: 1100px) {
  .product-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .home-loading { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 820px) {
  .product-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .home-loading { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .product-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .home-loading { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
