<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getHomeContentAPI, getHomeFeedAPI } from '@/apis/home'
import { getCategoryTreeAPI } from '@/apis/product'
import { useMemberStore } from '@/stores/member'
import type { FeedSection } from '@/apis/home'
import type { HomeContentResult, SmsHomeAdvertise } from '@/types/home'
import type { CategoryTreeNode, PmsProduct } from '@/types/product'
import {
  getCategoryOutline,
  type CategoryOutlineGroup,
} from '@/data/categoryOutline'

interface ProductSection {
  key: string
  title: string
  subtitle: string
  products: PmsProduct[]
}

interface QuickEntry {
  label: string
  path: string
  icon: string
}

const router = useRouter()
const memberStore = useMemberStore()
const loading = ref(true)
const loadError = ref('')
const homeContent = ref<HomeContentResult>({
  banners: [],
  newProducts: [],
  recommendProducts: [],
  subjects: [],
})
const categories = ref<CategoryTreeNode[]>([])
const feedSections = ref<FeedSection[]>([])
const activeBanner = ref(0)
const hoveredCategory = ref<CategoryTreeNode | null>(null)
let bannerTimer: ReturnType<typeof setInterval> | undefined

const quickEntries: QuickEntry[] = [
  { label: '领券中心', path: '/coupons', icon: '券' },
  { label: '品牌专区', path: '/brand', icon: '牌' },
  { label: '新品首发', path: '/new', icon: '新' },
  { label: '热销榜单', path: '/hot', icon: '榜' },
]

const banners = computed<SmsHomeAdvertise[]>(() => homeContent.value.banners)
const currentBanner = computed<SmsHomeAdvertise | undefined>(
  () => banners.value[activeBanner.value],
)
const hoveredCategoryOutline = computed<CategoryOutlineGroup[]>(() =>
  hoveredCategory.value ? getCategoryOutline(hoveredCategory.value.name) : [],
)
const visibleCategories = computed(() => {
  const names = new Set<string>()
  return categories.value
    .filter((category) => {
      if (names.has(category.name)) return false
      names.add(category.name)
      return true
    })
    .slice(0, 12)
})
const searchSuggestions = computed(() => {
  const section = feedSections.value.find((item) => item.sectionType === 'search_discovery')
  return section?.suggestions.slice(0, 8) ?? []
})

const productSections = computed<ProductSection[]>(() => {
  const result: ProductSection[] = []
  const seen = new Set<string>()

  for (const section of feedSections.value) {
    if (!section.products.length) continue
    const products = section.products.map((item) => ({
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
    }))
    result.push({
      key: section.sectionType,
      title: section.title,
      subtitle: section.subTitle,
      products,
    })
    products.forEach((product) => seen.add(product.id))
  }

  const fallbackProducts = [
    ...homeContent.value.recommendProducts,
    ...homeContent.value.newProducts,
  ].filter((product) => {
    if (seen.has(product.id)) return false
    seen.add(product.id)
    return true
  })

  if (fallbackProducts.length) {
    result.push({
      key: 'selected',
      title: '为你精选',
      subtitle: '口碑好物，逛到停不下来',
      products: fallbackProducts,
    })
  }
  return result
})

function productImage(product: PmsProduct): string {
  return product.defaultPic || ''
}

function formatPrice(price: number | null | undefined): string {
  return (price ?? 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function navigate(path: string): void {
  void router.push(path)
}

function searchCategory(category: CategoryTreeNode): void {
  void router.push({ path: '/search', query: { categoryId: category.id } })
}

function showCategoryDetails(category: CategoryTreeNode): void {
  hoveredCategory.value = category
}

function hideCategoryDetails(): void {
  hoveredCategory.value = null
}

function searchKeyword(keyword: string): void {
  void router.push({ path: '/search', query: { keyword } })
}

function openBanner(banner: SmsHomeAdvertise): void {
  if (!banner.url) return
  if (banner.url.startsWith('/')) {
    navigate(banner.url)
    return
  }
  window.location.assign(banner.url)
}

function startBannerTimer(): void {
  if (banners.value.length < 2) return
  bannerTimer = setInterval(() => {
    activeBanner.value = (activeBanner.value + 1) % banners.value.length
  }, 5000)
}

async function loadHome(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const [content, categoryTree] = await Promise.all([
      getHomeContentAPI(),
      getCategoryTreeAPI(),
    ])
    homeContent.value = content
    categories.value = categoryTree
    startBannerTimer()
    void loadFeed()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '首页加载失败'
  } finally {
    loading.value = false
  }
}

async function loadFeed(): Promise<void> {
  try {
    const feed = await getHomeFeedAPI(10)
    feedSections.value = feed.sections
  } catch {
    feedSections.value = []
  }
}

onMounted(loadHome)
onUnmounted(() => {
  if (bannerTimer) clearInterval(bannerTimer)
})
</script>

<template>
  <div class="home-page">
    <div v-if="loading" class="home-loading">
      <div v-for="index in 8" :key="index" class="skeleton-card" />
    </div>

    <div v-else-if="loadError" class="load-error">
      <strong>首页暂时走丢了</strong>
      <span>{{ loadError }}</span>
      <button @click="loadHome">重新加载</button>
    </div>

    <template v-else>
      <section class="hero-grid">
        <aside class="category-panel" @mouseleave="hideCategoryDetails">
          <div class="category-list">
            <button
              v-for="category in visibleCategories"
              :key="category.id"
              class="category-row"
              :class="{ active: hoveredCategory?.id === category.id }"
              @mouseenter="showCategoryDetails(category)"
              @focus="showCategoryDetails(category)"
              @click="searchCategory(category)"
            >
              <span class="category-dot" />
              <span>{{ category.name }}</span>
              <span class="category-children">
                {{ category.children?.slice(0, 2).map((item) => item.name).join(' / ') }}
              </span>
              <span class="category-arrow">›</span>
            </button>
          </div>

          <div v-if="hoveredCategory" class="category-flyout">
            <div class="category-flyout-heading">
              <button @click="searchCategory(hoveredCategory)">
                {{ hoveredCategory.name }}
                <span>查看全部 ›</span>
              </button>
            </div>
            <div v-if="hoveredCategoryOutline.length" class="category-groups">
              <section
                v-for="group in hoveredCategoryOutline"
                :key="group.title"
                :class="{ featured: group.featured }"
              >
                <button class="category-group-title" @click="searchKeyword(group.title)">
                  {{ group.title }} ›
                </button>
                <div class="category-links">
                  <button
                    v-for="item in group.items"
                    :key="item"
                    @click="searchKeyword(item)"
                  >
                    {{ item }}
                  </button>
                </div>
              </section>
            </div>
            <div v-else class="category-empty">
              点击查看 {{ hoveredCategory.name }} 下的全部商品
            </div>
          </div>
        </aside>

        <div class="hero-center">
          <button
            v-if="currentBanner"
            class="banner-card"
            :style="{ backgroundImage: `url(${currentBanner.pic})` }"
            @click="openBanner(currentBanner)"
          >
            <span class="banner-shade" />
            <span class="banner-copy">
              <small>SnapTrip 精选</small>
              <strong>{{ currentBanner.title || '发现今天的心动好物' }}</strong>
              <span>边逛边发现，让推荐更懂你</span>
            </span>
          </button>
          <div v-else class="banner-card banner-fallback">
            <span class="banner-copy">
              <small>SnapTrip 精选</small>
              <strong>发现今天的心动好物</strong>
              <span>商品内容由后台实时配置</span>
            </span>
          </div>
          <div v-if="banners.length > 1" class="banner-dots">
            <button
              v-for="(_, index) in banners"
              :key="index"
              :class="{ active: index === activeBanner }"
              @click="activeBanner = index"
            />
          </div>

          <div v-if="searchSuggestions.length" class="trend-strip">
            <strong>大家都在搜</strong>
            <button
              v-for="item in searchSuggestions"
              :key="item.query"
              @click="searchKeyword(item.query)"
            >
              {{ item.query }}
            </button>
          </div>
        </div>

        <aside class="user-panel">
          <div class="user-avatar">
            <img v-if="memberStore.avatar" :src="memberStore.avatar" alt="" />
            <span v-else>{{ memberStore.displayName?.slice(0, 1) || 'S' }}</span>
          </div>
          <strong>{{ memberStore.isLoggedIn ? `嗨，${memberStore.displayName}` : '欢迎来到 SnapTrip' }}</strong>
          <p>{{ memberStore.isLoggedIn ? '今天也来发现一点好东西' : '登录后解锁个性化推荐与会员权益' }}</p>
          <div class="user-actions">
            <button class="primary" @click="navigate(memberStore.isLoggedIn ? '/member' : '/login')">
              {{ memberStore.isLoggedIn ? '会员中心' : '立即登录' }}
            </button>
            <button @click="navigate('/coupons')">领券</button>
          </div>
          <div class="quick-grid">
            <button v-for="entry in quickEntries" :key="entry.path" @click="navigate(entry.path)">
              <span>{{ entry.icon }}</span>
              {{ entry.label }}
            </button>
          </div>
        </aside>
      </section>

      <section v-if="homeContent.subjects.length" class="subject-strip">
        <button
          v-for="subject in homeContent.subjects"
          :key="subject.id"
          class="subject-card"
          @click="searchKeyword(subject.title)"
        >
          <img v-if="subject.pic" :src="subject.pic" :alt="subject.title" />
          <span>
            <strong>{{ subject.title }}</strong>
            <small>{{ subject.categoryName || subject.summary || subject.description || '精选专题' }}</small>
          </span>
        </button>
      </section>

      <section
        v-for="section in productSections"
        :key="section.key"
        class="product-section"
      >
        <div class="section-heading">
          <div>
            <strong>{{ section.title }}</strong>
            <span>{{ section.subtitle }}</span>
          </div>
          <button @click="navigate('/search')">查看更多 ›</button>
        </div>
        <div class="product-grid">
          <button
            v-for="product in section.products"
            :key="product.id"
            class="product-card"
            @click="navigate(`/product/${product.id}`)"
          >
            <div class="product-image">
              <img v-if="productImage(product)" :src="productImage(product)" :alt="product.name" />
              <span v-else>SnapTrip</span>
              <em v-if="product.newStatus === 1">新品</em>
            </div>
            <div class="product-info">
              <p>{{ product.name }}</p>
              <small v-if="product.subTitle">{{ product.subTitle }}</small>
              <div>
                <strong><i>¥</i>{{ formatPrice(product.promotionPrice ?? product.price) }}</strong>
                <span>已售 {{ product.saleCount ?? 0 }}</span>
              </div>
            </div>
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.home-page { display: grid; gap: 22px; }
.hero-grid { display: grid; grid-template-columns: 240px minmax(0, 1fr) 250px; gap: 14px; min-height: 420px; }
.category-panel, .user-panel, .hero-center, .product-section, .subject-strip { background: #fff; border-radius: 18px; box-shadow: 0 6px 24px rgba(44, 31, 20, .06); }
.category-panel { position: relative; padding: 14px 0; overflow: visible; z-index: 12; }
.category-list { overflow: hidden; border-radius: 18px; }
.section-heading button { color: #999; font-size: 12px; }
.category-row { width: 100%; display: grid; grid-template-columns: 8px auto 1fr 12px; align-items: center; gap: 8px; padding: 8px 18px; color: #333; text-align: left; transition: .2s; }
.category-row:hover, .category-row.active { color: #ff5000; background: #fff3ed; }
.category-dot { width: 4px; height: 4px; border-radius: 50%; background: #ff5000; }
.category-children { color: #aaa; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.category-arrow { color: #bbb; }
.category-flyout { position: absolute; left: calc(100% - 2px); top: 0; width: 720px; min-height: 100%; padding: 20px 26px; border: 1px solid #ffe0d0; border-left: 3px solid #ff6a00; border-radius: 0 18px 18px 0; background: #fff; box-shadow: 16px 12px 32px rgba(44, 31, 20, .14); color: #333; z-index: 20; }
.category-flyout-heading { padding-bottom: 14px; margin-bottom: 14px; border-bottom: 1px solid #f3f3f3; }
.category-flyout-heading button { width: 100%; display: flex; align-items: center; justify-content: space-between; font-size: 18px; font-weight: 800; text-align: left; }
.category-flyout-heading span { color: #ff5000; font-size: 12px; font-weight: 600; }
.category-groups { display: grid; gap: 12px; max-height: 370px; overflow-y: auto; padding-right: 6px; }
.category-groups section { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 14px; align-items: start; }
.category-group-title { color: #333; font-size: 13px; font-weight: 700; line-height: 22px; text-align: left; white-space: nowrap; }
.category-group-title:hover { color: #ff5000; }
.category-links { display: flex; flex-wrap: wrap; gap: 5px 17px; min-height: 22px; }
.category-links button { color: #666; font-size: 12px; line-height: 22px; white-space: nowrap; }
.category-links button:hover { color: #ff5000; }
.category-groups section.featured .category-group-title,
.category-groups section.featured .category-links button { color: #ff5000; }
.category-empty { padding: 42px 0; color: #999; font-size: 13px; text-align: center; }
.hero-center { position: relative; padding: 12px; display: flex; flex-direction: column; }
.banner-card { min-height: 330px; width: 100%; border-radius: 14px; overflow: hidden; background-size: cover; background-position: center; position: relative; text-align: left; }
.banner-shade { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(0,0,0,.58), rgba(0,0,0,.04) 70%); }
.banner-fallback { background: linear-gradient(135deg, #ff6a00, #ffb900); }
.banner-copy { position: absolute; left: 34px; top: 50%; transform: translateY(-50%); color: white; display: grid; gap: 8px; z-index: 1; }
.banner-copy small { font-size: 13px; letter-spacing: 2px; }
.banner-copy strong { font-size: 30px; max-width: 420px; line-height: 1.2; }
.banner-copy span { font-size: 14px; opacity: .85; }
.banner-dots { position: absolute; left: 32px; bottom: 82px; display: flex; gap: 7px; }
.banner-dots button { width: 7px; height: 7px; border-radius: 999px; background: rgba(255,255,255,.55); }
.banner-dots button.active { width: 20px; background: #fff; }
.trend-strip { margin-top: 12px; display: flex; align-items: center; gap: 12px; overflow: hidden; white-space: nowrap; font-size: 12px; }
.trend-strip strong { color: #ff5000; }
.trend-strip button { color: #666; }
.trend-strip button:hover { color: #ff5000; }
.user-panel { padding: 26px 18px 18px; text-align: center; }
.user-avatar { width: 64px; height: 64px; margin: 0 auto 12px; border-radius: 50%; background: linear-gradient(135deg, #ff8a00, #ff5000); color: #fff; display: grid; place-items: center; font-size: 22px; overflow: hidden; }
.user-avatar img { width: 100%; height: 100%; object-fit: cover; }
.user-panel > strong { font-size: 16px; }
.user-panel > p { color: #999; font-size: 12px; margin: 8px 0 18px; line-height: 1.7; }
.user-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.user-actions button { border: 1px solid #ff5000; color: #ff5000; border-radius: 999px; padding: 8px; font-size: 13px; }
.user-actions .primary { background: linear-gradient(90deg, #ff7900, #ff5000); color: #fff; }
.quick-grid { margin-top: 22px; padding-top: 18px; border-top: 1px solid #f3f3f3; display: grid; grid-template-columns: 1fr 1fr; gap: 14px 8px; }
.quick-grid button { color: #666; font-size: 12px; display: grid; gap: 5px; justify-items: center; }
.quick-grid span { width: 32px; height: 32px; border-radius: 10px; background: #fff4ee; color: #ff5000; display: grid; place-items: center; font-weight: 800; }
.subject-strip { padding: 14px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.subject-card { min-width: 0; display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 12px; background: #fafafa; text-align: left; }
.subject-card img { width: 54px; height: 54px; border-radius: 10px; object-fit: cover; }
.subject-card span { min-width: 0; display: grid; gap: 5px; }
.subject-card strong, .subject-card small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.subject-card small { color: #999; }
.product-section { padding: 20px; }
.section-heading { display: flex; align-items: end; justify-content: space-between; margin-bottom: 16px; }
.section-heading > div { display: flex; align-items: baseline; gap: 10px; }
.section-heading strong { font-size: 22px; color: #222; }
.section-heading span { color: #999; font-size: 12px; }
.product-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.product-card { overflow: hidden; border: 1px solid #f2f2f2; border-radius: 14px; background: #fff; text-align: left; transition: .25s; }
.product-card:hover { transform: translateY(-4px); border-color: #ffd8c3; box-shadow: 0 14px 30px rgba(255, 80, 0, .12); }
.product-image { aspect-ratio: 1; background: #f7f7f7; position: relative; display: grid; place-items: center; color: #bbb; font-weight: 800; }
.product-image img { width: 100%; height: 100%; object-fit: cover; }
.product-image em { position: absolute; top: 8px; left: 8px; background: #ff5000; color: #fff; border-radius: 5px; padding: 3px 7px; font-size: 10px; font-style: normal; }
.product-info { padding: 12px; }
.product-info p { height: 40px; color: #333; line-height: 20px; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
.product-info small { display: block; color: #ff5000; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.product-info > div { margin-top: 10px; display: flex; justify-content: space-between; align-items: baseline; }
.product-info strong { color: #ff5000; font-size: 19px; }
.product-info i { font-size: 12px; font-style: normal; }
.product-info span { color: #aaa; font-size: 11px; }
.home-loading { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.skeleton-card { height: 260px; border-radius: 18px; background: linear-gradient(90deg, #f3f3f3, #fafafa, #f3f3f3); background-size: 200% 100%; animation: pulse 1.3s infinite; }
.load-error { min-height: 360px; display: grid; place-items: center; align-content: center; gap: 10px; background: #fff; border-radius: 18px; color: #999; }
.load-error strong { color: #333; font-size: 20px; }
.load-error button { margin-top: 8px; border-radius: 999px; background: #ff5000; color: #fff; padding: 8px 22px; }
@keyframes pulse { to { background-position: -200% 0; } }
@media (max-width: 1100px) {
  .hero-grid { grid-template-columns: 210px minmax(0, 1fr); }
  .user-panel { display: none; }
  .product-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .hero-grid { grid-template-columns: 1fr; }
  .category-panel { display: none; }
  .banner-card { min-height: 260px; }
  .banner-copy strong { font-size: 23px; }
  .subject-strip { grid-template-columns: 1fr 1fr; }
  .product-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .section-heading span { display: none; }
}
</style>
