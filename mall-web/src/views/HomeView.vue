<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHomeContentAPI, getHomeFeedAPI } from '@/apis/home'
import type { FeedSection } from '@/apis/home'
import type { HomeContentResult } from '@/types/home'
import type { PmsProduct } from '@/types/product'
import ProductCard from '@/components/product/ProductCard.vue'

const PAGE_SIZE = 24

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

/** 所有商品列表 — ref 以支持追加 */
const allProducts = ref<PmsProduct[]>([])

/** 已加载商品 ID 集合，用于去重 */
const loadedProductIds = new Set<string | number>()

/** 翻页状态 */
const currentOffset = ref(0)
const hasMore = ref(true)
const loadingMore = ref(false)

/** 哨兵元素 ref */
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

type FeedProductItem = FeedSection['products'][number]

/** 将 FeedProduct 转为 PmsProduct */
function feedProductToPmsProduct(item: FeedProductItem): PmsProduct {
  return {
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
  }
}

/** 将 section.products 去重追加到 allProducts */
function appendProducts(products: FeedProductItem[]): number {
  let added = 0
  for (const item of products) {
    if (loadedProductIds.has(item.productId)) continue
    loadedProductIds.add(item.productId)
    allProducts.value.push(feedProductToPmsProduct(item))
    added++
  }
  return added
}

/** 追加 homeContent 中的旧版商品 (banners 后首次) */
function appendLegacyProducts(): void {
  for (const product of homeContent.value.recommendProducts) {
    if (loadedProductIds.has(product.id)) continue
    loadedProductIds.add(product.id)
    allProducts.value.push(product)
  }
  for (const product of homeContent.value.newProducts) {
    if (loadedProductIds.has(product.id)) continue
    loadedProductIds.add(product.id)
    allProducts.value.push(product)
  }
}

/** 加载 feed — offset=0 时重置，offset>0 时追加 */
async function loadFeed(offset: number, excludeIds: string[] = []): Promise<void> {
  try {
    const feed = await getHomeFeedAPI(PAGE_SIZE, offset, excludeIds)
    if (offset === 0) {
      feedSections.value = feed.sections
    }
    let totalAdded = 0
    for (const section of feed.sections) {
      totalAdded += appendProducts(section.products)
    }
    if (totalAdded === 0) {
      hasMore.value = false
    }
  } catch {
    if (offset === 0) {
      feedSections.value = []
    }
    hasMore.value = false
  }
}

const MAX_PRODUCTS = 200 // 安全上限，超过此数量强制不再加载

/** 加载更多 — 纯 offset 分页 + 哨兵重绑定 */
async function loadMore(): Promise<void> {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  currentOffset.value += PAGE_SIZE
  const excludeIds = Array.from(loadedProductIds).slice(-80).map(String)
  await loadFeed(currentOffset.value, excludeIds)
  loadingMore.value = false
  // 安全兜底：商品数达上限或 offset 过大时终止
  if (allProducts.value.length >= MAX_PRODUCTS || currentOffset.value >= 300) {
    hasMore.value = false
  }
  await nextTick()
  teardownObserver()
  if (sentinelRef.value && hasMore.value) setupObserver()
}

/** 设置滚动监听 */
function setupObserver(): void {
  if (!sentinelRef.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loadingMore.value) {
        loadMore()
      }
    },
    {
      // 预触底: 哨兵在视口下方 200px 时即触发
      rootMargin: '0px 0px 200px 0px',
    },
  )
  observer.observe(sentinelRef.value)
}

function teardownObserver(): void {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

/** 哨兵插入 DOM 后绑定观察器 */
watch(sentinelRef, (el) => {
  teardownObserver()
  if (el) setupObserver()
})

async function loadHome(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    // 重置状态
    allProducts.value = []
    loadedProductIds.clear()
    currentOffset.value = 0
    hasMore.value = true
    loadingMore.value = false

    const [content] = await Promise.all([
      getHomeContentAPI(),
    ])
    homeContent.value = content

    // 加载首页 feed
    await loadFeed(0)

    // 追加旧版商品
    appendLegacyProducts()

    // feed 加载完成后绑定滚动监听
    await nextTick()
    teardownObserver()
    if (sentinelRef.value) setupObserver()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '首页加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadHome)
onBeforeUnmount(teardownObserver)
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

      <!-- 加载更多骨架 -->
      <div v-if="loadingMore" class="home-loading" style="margin-top: 14px">
        <div v-for="index in 6" :key="'more-' + index" class="skeleton-card" />
      </div>

      <!-- 底部提示 -->
      <div class="feed-footer">
        <span v-if="!hasMore && allProducts.length > 0">— 已经到底了 —</span>
      </div>

      <!-- 预触底哨兵 -->
      <div ref="sentinelRef" class="scroll-sentinel" />
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

.feed-footer {
  display: grid;
  place-items: center;
  padding: 24px 0 32px;
  color: #bbb;
  font-size: 13px;
}

.scroll-sentinel {
  height: 1px;
  width: 100%;
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
