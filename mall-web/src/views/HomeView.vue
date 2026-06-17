<script setup lang="ts">
/**
 * ============================================
 * 商城首页 (HomeView)
 * 参考京东/天猫/淘宝 PC 端经典布局
 * ============================================
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getHomeContentAPI, getHomeFeedAPI, getPersonalizedRecommendationsAPI, type FeedSection } from '@/apis/home'
import type { PmsProduct } from '@/types/product'
import type { PmsBrand } from '@/types/brand'
import type { SmsHomeAdvertise, HomeFlashPromotion, CmsSubject } from '@/types/home'

const router = useRouter()

const loading = ref(false)

// ===== 轮播图（从 API）=====
const currentBanner = ref(0)
let bannerTimer: ReturnType<typeof setInterval> | null = null

const banners = ref<SmsHomeAdvertise[]>([])

const startBannerAutoPlay = () => {
  if (banners.value.length <= 1) return
  bannerTimer = setInterval(() => {
    currentBanner.value = (currentBanner.value + 1) % banners.value.length
  }, 4000)
}

const stopBannerAutoPlay = () => {
  if (bannerTimer) {
    clearInterval(bannerTimer)
    bannerTimer = null
  }
}

const goToBanner = (index: number) => {
  currentBanner.value = index
  stopBannerAutoPlay()
  startBannerAutoPlay()
}

// ===== 多级商品分类（前端静态数据 — 后端暂无3级结构+emoji图标）=====
interface SubCategory {
  name: string
  items: string[]
}

interface Category {
  name: string
  icon: string
  subCategories: SubCategory[]
}

const categories = ref<Category[]>([
  {
    name: '手机数码',
    icon: '📱',
    subCategories: [
      { name: '手机通讯', items: ['5G手机', '游戏手机', '拍照手机', '全面屏手机', '对讲机', '以旧换新'] },
      { name: '手机配件', items: ['手机壳', '贴膜', '移动电源', '数据线', '充电器', '手机存储卡', '创意配件'] },
      { name: '摄影摄像', items: ['数码相机', '微单相机', '单反相机', '拍立得', '运动相机', '摄像机', '镜头'] },
      { name: '数码配件', items: ['存储卡', '读卡器', '三脚架', '相机包', '滤镜', '电池/充电器'] },
    ],
  },
  {
    name: '电脑办公',
    icon: '💻',
    subCategories: [
      { name: '电脑整机', items: ['轻薄本', '游戏本', '台式机', '一体机', '平板电脑', '服务器'] },
      { name: '电脑配件', items: ['显示器', 'CPU', '主板', '显卡', '硬盘', '内存', '机箱', '电源'] },
      { name: '外设产品', items: ['鼠标', '键盘', 'U盘', '移动硬盘', '鼠标垫', '摄像头', '线缆'] },
      { name: '办公设备', items: ['投影机', '打印机', '碎纸机', '考勤机', '保险柜', '白板'] },
    ],
  },
  {
    name: '家用电器',
    icon: '🏠',
    subCategories: [
      { name: '电视', items: ['超薄电视', '全面屏', '4K超清', '智能电视', 'OLED电视', '98英寸'] },
      { name: '空调', items: ['壁挂式', '柜机', '中央空调', '移动空调', '变频空调', '一级能效'] },
      { name: '冰箱', items: ['对开门', '三门', '双门', '冷柜/冰吧', '酒柜', '多门'] },
      { name: '洗衣机', items: ['滚筒', '洗烘一体', '波轮', '迷你', '烘干机', '双缸'] },
      { name: '厨卫大电', items: ['油烟机', '燃气灶', '洗碗机', '电热水器', '燃气热水器', '消毒柜'] },
    ],
  },
  {
    name: '家居家装',
    icon: '🛋️',
    subCategories: [
      { name: '家纺', items: ['床品套件', '被子', '枕头', '蚊帐', '凉席', '毛巾浴巾', '地毯地垫'] },
      { name: '灯具', items: ['吸顶灯', '吊灯', '台灯', '筒灯射灯', '灯带', '户外灯'] },
      { name: '家具', items: ['沙发', '床', '床垫', '餐桌', '衣柜', '茶几', '鞋柜'] },
      { name: '厨具', items: ['炒锅', '压力锅', '蒸锅', '炖锅', '煎锅', '汤锅', '奶锅'] },
      { name: '水具酒具', items: ['保温杯', '茶壶', '咖啡具', '玻璃杯', '陶瓷杯', '酒具'] },
    ],
  },
  {
    name: '服装服饰',
    icon: '👗',
    subCategories: [
      { name: '女装', items: ['连衣裙', 'T恤', '衬衫', '卫衣', '外套', '牛仔裤', '半身裙'] },
      { name: '男装', items: ['T恤', '衬衫', 'POLO衫', '夹克', '西服', '休闲裤', '牛仔裤'] },
      { name: '童装', items: ['套装', '上衣', '裤子', '裙子', '亲子装', '童鞋', '婴儿装'] },
      { name: '内衣', items: ['文胸', '内裤', '睡衣', '保暖内衣', '袜子', '塑身衣'] },
      { name: '配饰', items: ['围巾', '帽子', '手套', '皮带', '太阳镜', '首饰'] },
    ],
  },
  {
    name: '美妆个护',
    icon: '💄',
    subCategories: [
      { name: '面部护肤', items: ['洁面', '爽肤水', '乳液/面霜', '精华', '面膜', '防晒', '眼霜'] },
      { name: '彩妆香氛', items: ['口红', '粉底', '眼影', '香水', '眉笔', '腮红', '卸妆'] },
      { name: '美发护发', items: ['洗发水', '护发素', '染发', '造型', '发膜', '精油'] },
      { name: '身体护理', items: ['沐浴露', '身体乳', '护手霜', '剃须', '脱毛', '足浴'] },
      { name: '口腔护理', items: ['牙膏', '牙刷', '漱口水', '牙线', '电动牙刷', '冲牙器'] },
    ],
  },
  {
    name: '运动户外',
    icon: '⚽',
    subCategories: [
      { name: '运动鞋包', items: ['跑步鞋', '休闲鞋', '篮球鞋', '足球鞋', '板鞋', '运动包'] },
      { name: '运动服饰', items: ['运动T恤', '运动裤', '卫衣', '夹克', '运动套装', '健身服'] },
      { name: '健身训练', items: ['跑步机', '动感单车', '哑铃', '瑜伽垫', '健腹轮', '跳绳'] },
      { name: '户外装备', items: ['帐篷', '背包', '睡袋', '登山鞋', '冲锋衣', '户外照明'] },
      { name: '体育用品', items: ['乒乓球', '羽毛球', '篮球', '足球', '网球', '台球'] },
    ],
  },
  {
    name: '食品生鲜',
    icon: '🍎',
    subCategories: [
      { name: '新鲜水果', items: ['苹果', '橙子', '芒果', '葡萄', '西瓜', '车厘子', '榴莲'] },
      { name: '海鲜水产', items: ['虾类', '鱼类', '蟹类', '贝类', '海参', '鱿鱼', '小龙虾'] },
      { name: '肉禽蛋品', items: ['牛肉', '猪肉', '羊肉', '鸡肉', '鸡蛋', '牛排', '鸡翅'] },
      { name: '粮油调味', items: ['大米', '食用油', '面粉', '酱油', '调味酱', '干货'] },
      { name: '休闲食品', items: ['坚果', '饼干', '巧克力', '糖果', '肉干', '蜜饯', '薯片'] },
    ],
  },
  {
    name: '母婴玩具',
    icon: '🍼',
    subCategories: [
      { name: '奶粉', items: ['1段', '2段', '3段', '4段', '羊奶粉', '有机奶粉', '特配奶粉'] },
      { name: '尿裤湿巾', items: ['纸尿裤', '拉拉裤', '婴儿湿巾', '尿垫', '婴儿纸巾'] },
      { name: '喂养用品', items: ['奶瓶', '奶嘴', '吸奶器', '辅食机', '暖奶器', '儿童餐具'] },
      { name: '洗护用品', items: ['沐浴露', '润肤霜', '护臀霜', '爽身粉', '湿巾', '洗衣液'] },
      { name: '玩具乐器', items: ['积木', '益智玩具', '毛绒玩具', '遥控车', '乐器', '模型'] },
    ],
  },
  {
    name: '图书文娱',
    icon: '📚',
    subCategories: [
      { name: '图书', items: ['文学', '小说', '童书', '教育', '科技', '历史', '艺术'] },
      { name: '电子书', items: ['小说', '文学', '经管', '社科', '科技', '原版'] },
      { name: '音像', items: ['音乐', '影视', '教育', '纪录片', '动画片'] },
      { name: '文具', items: ['笔类', '本册', '办公文具', '画具', '学生文具', '文件夹'] },
    ],
  },
])

// 当前 hover 的分类索引
const hoveredCategoryIndex = ref(-1)

// ===== 秒杀（从 API）=====
const homeFlashPromotion = ref<HomeFlashPromotion | null>(null)
const seckillItems = ref<PmsProduct[]>([])

// 秒杀倒计时
const seckillHours = ref(0)
const seckillMinutes = ref(0)
const seckillSeconds = ref(0)

let seckillTimer: ReturnType<typeof setInterval> | null = null

function updateSeckillCountdown() {
  if (!homeFlashPromotion.value?.endTime) return
  const diff = Math.max(0, new Date(homeFlashPromotion.value.endTime).getTime() - Date.now())
  seckillHours.value = Math.floor(diff / 3600000)
  seckillMinutes.value = Math.floor((diff % 3600000) / 60000)
  seckillSeconds.value = Math.floor((diff % 60000) / 1000)
}

const startSeckillCountdown = () => {
  updateSeckillCountdown()
  seckillTimer = setInterval(updateSeckillCountdown, 1000)
}

// ===== 热门推荐 & 新品 & 品牌（从 API）=====
const hotProducts = ref<PmsProduct[]>([])
const newProducts = ref<PmsProduct[]>([])
const personalizedProducts = ref<PmsProduct[]>([])
const personalized = ref(false)  // 是否成功获取个性化推荐
const brands = ref<PmsBrand[]>([])
const feedSections = ref<FeedSection[]>([])  // 多维度推荐 feed

/** 根据商品属性派生标签 */
function getProductTag(p: PmsProduct): string | null {
  if (p.promotionType === 5) return '限时'
  if (p.promotionType === 1) return '优惠'
  if (p.promotionType === 4) return '满减'
  if (p.newStatus === 1) return '新品'
  if ((p.recommendStatus ?? 0) === 1) return '推荐'
  return null
}

/** 加载首页聚合数据 */
async function loadHomeContent() {
  loading.value = true
  try {
    const data = await getHomeContentAPI()
    banners.value = data.banners || []
    hotProducts.value = data.recommendProducts || []
    newProducts.value = data.newProducts || []
    startBannerAutoPlay()
    startSeckillCountdown()

    // 异步加载个性化推荐 & 多维度 feed (不阻塞首页渲染)
    loadPersonalizedRecommendations()
    loadHomeFeed()
  } catch (err: any) {
    console.error('加载首页失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

/** 加载多维度推荐 Feed (5-row) */
async function loadHomeFeed() {
  try {
    const res = await getHomeFeedAPI(10)
    if (res.sections && res.sections.length > 0) {
      feedSections.value = res.sections
      // 从 feed 中提取猜你喜欢 section 用于兼容旧逻辑
      const gyl = res.sections.find(s => s.section_type === 'guess_you_like')
      if (gyl && gyl.products.length > 0) {
        personalized.value = true
      }
    }
  } catch (err: any) {
    console.log('多维度推荐暂不可用:', err?.message || err)
  }
}

/** 加载个性化推荐 (由 AI Agent 流水线生成) — 保留兼容 */
async function loadPersonalizedRecommendations() {
  try {
    const res = await getPersonalizedRecommendationsAPI({ scene: 'homepage', numItems: 10 })
    const products = res.products || []
    if (products.length > 0) {
      personalizedProducts.value = products.map((p: any) => ({
        id: p.productId,
        name: p.name,
        price: p.price,
        defaultPic: p.imageUrl,
        brandName: p.brandName,
        sale: p.saleCount,
        subTitle: p.marketingCopy || '',
      })) as unknown as PmsProduct[]
      personalized.value = true
    }
  } catch (err: any) {
    console.log('个性化推荐暂不可用, 使用默认推荐:', err?.message || err)
    personalized.value = false
  }
}

/** 将 FeedProduct 转为 PmsProduct 兼容格式 */
function feedToProduct(fp: any): PmsProduct {
  return {
    id: fp.product_id,
    name: fp.name,
    price: fp.price,
    defaultPic: fp.image_url,
    brandName: fp.brand_name,
    saleCount: fp.sale_count,
    subTitle: fp.marketing_copy || '',
    promotionType: fp.promotion_type || 0,
    newStatus: fp.new_status || 0,
    recommendStatus: fp.recommend_status || 0,
  } as unknown as PmsProduct
}

/** section 类型 → 主题色 class 映射 */
function sectionAccentClass(type: string, kind: 'bar' | 'border' | 'hover' = 'bar'): string {
  const map: Record<string, { bar: string; border: string; hover: string }> = {
    guess_you_like:     { bar: 'bg-purple-600', border: 'border-purple-100', hover: 'hover:border-purple-200' },
    trending_now:       { bar: 'bg-red-600',     border: 'border-red-100',     hover: 'hover:border-red-200' },
    new_arrivals:       { bar: 'bg-green-500',   border: 'border-green-100',   hover: 'hover:border-green-200' },
    recently_viewed:    { bar: 'bg-blue-500',    border: 'border-blue-100',    hover: 'hover:border-blue-200' },
    search_discovery:   { bar: 'bg-orange-500',  border: 'border-orange-100',  hover: 'hover:border-orange-200' },
  }
  return map[type]?.[kind] || map.trending_now[kind]
}

// ===== 导航到商品详情 =====
const goProductDetail = (id: string) => {
  if (!id || id === 'undefined') return
  router.push(`/product/${id}`)
}

onMounted(() => {
  loadHomeContent()
})

onUnmounted(() => {
  stopBannerAutoPlay()
  if (seckillTimer) clearInterval(seckillTimer)
})
</script>

<template>
  <div class="home-page">
    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-40 text-gray-400">加载中...</div>

    <template v-else>
    <!-- ======================== 首屏区域 ======================== -->
    <section class="hero-section mb-6">
      <div class="flex h-[400px] gap-0">
        <!-- 左侧：商品分类导航 (200px) -->
        <aside
          class="w-[200px] bg-white rounded-l-xl shadow-sm flex-shrink-0 relative z-20"
          @mouseleave="hoveredCategoryIndex = -1"
        >
          <div class="py-2">
            <div
              v-for="(cat, index) in categories"
              :key="index"
              class="group/cat"
              @mouseenter="hoveredCategoryIndex = index"
            >
              <div
                :class="[
                  'flex items-center gap-2 px-4 py-[7px] text-sm cursor-pointer transition-colors',
                  hoveredCategoryIndex === index
                    ? 'bg-red-600 text-white'
                    : 'text-gray-600 hover:bg-red-50 hover:text-red-600',
                ]"
              >
                <span class="text-base">{{ cat.icon }}</span>
                <span class="font-medium truncate">{{ cat.name }}</span>
              </div>
            </div>
          </div>

          <!-- 悬浮展开的二级分类面板 -->
          <div
            v-if="hoveredCategoryIndex >= 0"
            class="absolute left-[200px] top-0 w-[680px] min-h-[400px] bg-white rounded-r-xl shadow-xl border border-gray-100 p-6 z-30"
          >
            <div class="grid grid-cols-3 gap-x-6 gap-y-5">
              <div
                v-for="(sub, sIdx) in categories[hoveredCategoryIndex].subCategories"
                :key="sIdx"
              >
                <h4 class="text-sm font-bold text-gray-900 mb-2 pb-1 border-b border-gray-100">
                  {{ sub.name }}
                </h4>
                <div class="flex flex-wrap gap-2 mt-2">
                  <button
                    v-for="(item, iIdx) in sub.items"
                    :key="iIdx"
                    class="text-xs text-gray-500 hover:text-red-600 transition-colors"
                    @click="router.push('/category')"
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右侧：轮播图 -->
        <div class="flex-1 relative overflow-hidden rounded-r-xl" @mouseenter="stopBannerAutoPlay" @mouseleave="startBannerAutoPlay">
          <!-- 轮播图片 -->
          <div
            class="flex h-full transition-transform duration-500 ease-out"
            :style="{ transform: `translateX(-${currentBanner * 100}%)` }"
          >
            <div
              v-for="banner in banners"
              :key="banner.id"
              class="w-full h-full flex-shrink-0 relative cursor-pointer"
              @click="router.push(banner.url || '/search')"
            >
              <img
                :src="banner.pic"
                :alt="banner.name"
                class="w-full h-full object-cover"
              />
              <!-- 文字遮罩 -->
              <div class="absolute inset-0 bg-gradient-to-r from-black/40 via-transparent to-transparent" />
              <div class="absolute left-8 top-1/2 -translate-y-1/2 text-white">
                <h2 class="text-3xl font-bold mb-2 drop-shadow-lg">{{ banner.name }}</h2>
              </div>
            </div>
          </div>

          <!-- 左右切换按钮 -->
          <button
            class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/30 hover:bg-black/50 text-white rounded-full flex items-center justify-center transition-colors backdrop-blur-sm"
            @click="goToBanner((currentBanner - 1 + banners.length) % banners.length)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/30 hover:bg-black/50 text-white rounded-full flex items-center justify-center transition-colors backdrop-blur-sm"
            @click="goToBanner((currentBanner + 1) % banners.length)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <!-- 底部指示器 -->
          <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2">
            <button
              v-for="(_, index) in banners"
              :key="index"
              :class="[
                'h-2 rounded-full transition-all duration-300',
                currentBanner === index ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/70',
              ]"
              @click="goToBanner(index)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ======================== 秒杀专区 ======================== -->
    <section v-if="seckillItems.length" class="seckill-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-red-600 to-red-500">
          <div class="flex items-center gap-4">
            <h2 class="text-xl font-bold text-white">限时秒杀</h2>
            <div class="flex items-center gap-1 text-white">
              <span class="text-sm">距结束</span>
              <div class="flex items-center gap-1">
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillHours).padStart(2, '0') }}</span>
                <span class="text-xs">:</span>
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillMinutes).padStart(2, '0') }}</span>
                <span class="text-xs">:</span>
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillSeconds).padStart(2, '0') }}</span>
              </div>
            </div>
          </div>
          <button class="text-sm text-white/90 hover:text-white flex items-center gap-1 transition-colors" @click="router.push('/hot')">
            查看全部
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <!-- 秒杀商品横向滚动 -->
        <div class="flex gap-4 p-5 overflow-x-auto">
          <button
            v-for="item in seckillItems"
            :key="item.id"
            class="flex-shrink-0 w-[200px] group text-left"
            @click="goProductDetail(item.id)"
          >
            <div class="aspect-square rounded-lg bg-gray-50 overflow-hidden mb-2">
              <img :src="item.defaultPic" :alt="item.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            </div>
            <p class="text-xs text-gray-700 line-clamp-2 mb-2 h-8 leading-4">{{ item.name }}</p>
            <div class="flex items-baseline gap-2">
              <span class="text-red-600 font-bold text-base">&yen;{{ item.promotionPrice || item.price }}</span>
              <span class="text-gray-400 text-xs line-through">&yen;{{ item.originalPrice }}</span>
            </div>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 品牌推荐 ======================== -->
    <section v-if="brands.length" class="brand-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-bold text-gray-900">热门品牌</h2>
          <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/brand')">查看全部 &rarr;</button>
        </div>
        <div class="grid grid-cols-10 gap-3">
          <button
            v-for="brand in brands"
            :key="brand.id"
            class="group flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-md transition-all"
            @click="router.push(`/brand/${brand.id}`)"
          >
            <div class="w-12 h-12 rounded-full bg-gray-50 overflow-hidden flex items-center justify-center">
              <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover group-hover:scale-110 transition-transform" />
            </div>
            <span class="text-xs text-gray-600 truncate w-full text-center">{{ brand.name }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 多维度推荐板块 (Feed) ======================== -->
    <template v-if="feedSections.length">
      <section
        v-for="section in feedSections"
        :key="section.section_type"
        v-show="section.section_type !== 'search_discovery' ? section.products.length > 0 : section.suggestions.length > 0"
        class="feed-section mb-6"
      >
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <!-- 区块头部 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div :class="['w-1 h-5 rounded-full', sectionAccentClass(section.section_type, 'bar')]" />
              <h2 class="text-lg font-bold text-gray-900">{{ section.title }}</h2>
              <span class="text-xs text-gray-400">{{ section.sub_title }}</span>
            </div>
            <button
              v-if="section.section_type !== 'search_discovery'"
              class="text-sm text-gray-500 hover:text-red-600 transition-colors"
              @click="router.push(section.section_type === 'new_arrivals' ? '/new' : '/hot')"
            >查看更多 &rarr;</button>
          </div>

          <!-- 搜索发现：标签云布局 -->
          <div
            v-if="section.section_type === 'search_discovery' && section.suggestions.length"
            class="px-6 py-4"
          >
            <div class="flex flex-wrap gap-2">
              <button
                v-for="item in section.suggestions"
                :key="item.query"
                class="px-4 py-2 bg-orange-50 hover:bg-orange-100 text-orange-700 rounded-full text-sm transition-colors hover:shadow-sm"
                @click="router.push(`/search?q=${encodeURIComponent(item.query)}`)"
              >
                {{ item.query }}
                <span class="text-xs text-orange-400 ml-1">({{ item.count }})</span>
              </button>
            </div>
          </div>

          <!-- 商品板块：5列网格布局 -->
          <div
            v-if="section.section_type !== 'search_discovery' && section.products.length"
            class="p-5 grid grid-cols-5 gap-4"
          >
            <button
              v-for="product in section.products"
              :key="product.product_id"
              :class="[
                'group text-left bg-white rounded-lg border border-gray-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden',
                sectionAccentClass(section.section_type, 'border'),
                sectionAccentClass(section.section_type, 'hover'),
              ]"
              @click="goProductDetail(product.product_id)"
            >
              <!-- 商品图片 -->
              <div class="aspect-square bg-gray-50 overflow-hidden relative">
                <img
                  :src="product.image_url"
                  :alt="product.name"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <!-- 标签 -->
                <span
                  v-if="product.promotion_type"
                  class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-2 py-0.5 rounded font-medium"
                >
                  {{ product.promotion_type === 5 ? '限时' : product.promotion_type === 1 ? '优惠' : product.promotion_type === 4 ? '满减' : '特惠' }}
                </span>
                <span
                  v-else-if="product.new_status"
                  class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded font-medium"
                >NEW</span>
                <span
                  v-else-if="section.section_type === 'guess_you_like' && product.score > 0.8"
                  class="absolute top-2 left-2 bg-purple-600 text-white text-[10px] px-2 py-0.5 rounded font-medium"
                >AI推荐</span>
              </div>
              <!-- 商品信息 -->
              <div class="p-3">
                <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">
                  {{ product.name }}
                </p>
                <!-- AI 文案 -->
                <p v-if="product.marketing_copy" class="text-xs text-purple-500 mb-1 line-clamp-1 italic">{{ product.marketing_copy }}</p>
                <div class="flex items-baseline gap-2">
                  <span class="text-red-600 font-bold text-base">
                    <span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.{{ String((product.price % 1).toFixed(2)).split('.')[1] }}</span>
                  </span>
                </div>
                <!-- 销量或评分 -->
                <p class="text-xs text-gray-400 mt-1">
                  已售 {{ (product.sale_count ?? 0) >= 10000 ? ((product.sale_count ?? 0) / 10000).toFixed(1) + '万' : (product.sale_count ?? 0) }}
                  <span v-if="section.section_type === 'guess_you_like' && product.score" class="ml-2 text-purple-400">匹配 {{ (product.score * 100).toFixed(0) }}%</span>
                </p>
              </div>
            </button>
          </div>
        </div>
      </section>
    </template>

    <!-- ======================== 降级：默认推荐 (无 Feed 时) ======================== -->
    <template v-else>
      <!-- 热门推荐 -->
      <section v-if="hotProducts.length" class="hot-section mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-1 h-5 bg-red-600 rounded-full" />
              <h2 class="text-lg font-bold text-gray-900">热门推荐</h2>
              <span class="text-xs text-gray-400">精选好物，品质保障</span>
            </div>
            <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/hot')">查看更多 &rarr;</button>
          </div>
          <div class="p-5 grid grid-cols-5 gap-4">
            <button
              v-for="product in hotProducts"
              :key="product.id"
              class="group text-left bg-white rounded-lg border border-gray-100 hover:border-red-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
              @click="goProductDetail(product.id)"
            >
              <div class="aspect-square bg-gray-50 overflow-hidden relative">
                <img :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                <span v-if="getProductTag(product)" class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-2 py-0.5 rounded font-medium">{{ getProductTag(product) }}</span>
              </div>
              <div class="p-3">
                <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
                <div class="flex items-baseline gap-2">
                  <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.{{ String((product.price % 1).toFixed(2)).split('.')[1] }}</span></span>
                  <span v-if="product.originalPrice" class="text-gray-400 text-xs line-through">&yen;{{ product.originalPrice }}</span>
                </div>
                <p class="text-xs text-gray-400 mt-1">已售 {{ (product.saleCount ?? 0) >= 10000 ? ((product.saleCount ?? 0) / 10000).toFixed(1) + '万' : (product.saleCount ?? 0) }}</p>
              </div>
            </button>
          </div>
        </div>
      </section>

      <!-- 新品上架 -->
      <section v-if="newProducts.length" class="new-section mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-1 h-5 bg-green-500 rounded-full" />
              <h2 class="text-lg font-bold text-gray-900">新品上架</h2>
              <span class="text-xs text-gray-400">新鲜好物，抢先体验</span>
            </div>
            <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/new')">查看更多 &rarr;</button>
          </div>
          <div class="p-5 grid grid-cols-5 gap-4">
            <button
              v-for="product in newProducts"
              :key="product.id"
              class="group text-left bg-white rounded-lg border border-gray-100 hover:border-green-200 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
              @click="goProductDetail(product.id)"
            >
              <div class="aspect-square bg-gray-50 overflow-hidden relative">
                <img :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                <span class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded font-medium">NEW</span>
              </div>
              <div class="p-3">
                <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-green-600 transition-colors">{{ product.name }}</p>
                <div class="flex items-baseline gap-2">
                  <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.{{ String((product.price % 1).toFixed(2)).split('.')[1] }}</span></span>
                  <span v-if="product.originalPrice" class="text-gray-400 text-xs line-through">&yen;{{ product.originalPrice }}</span>
                </div>
                <p class="text-xs text-gray-400 mt-1">已售 {{ product.saleCount ?? 0 }}</p>
              </div>
            </button>
          </div>
        </div>
      </section>

      <!-- 为你推荐 -->
      <section v-if="hotProducts.length || newProducts.length || personalized" class="recommend-section">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="flex items-center justify-center px-6 py-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-px bg-gray-200" />
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <h2 class="text-lg font-bold text-gray-900">{{ personalized ? 'AI 为你推荐' : '为你推荐' }}</h2>
              <div class="w-8 h-px bg-gray-200" />
            </div>
          </div>
          <div class="p-5 grid grid-cols-5 gap-4">
            <button
              v-for="product in (personalized ? personalizedProducts : [...hotProducts, ...newProducts].slice(0, 10))"
              :key="`rec-${product.id}`"
              class="group text-left bg-white rounded-lg border border-gray-100 hover:border-red-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
              @click="goProductDetail(product.id)"
            >
              <div class="aspect-square bg-gray-50 overflow-hidden relative">
                <img :src="product.defaultPic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              </div>
              <div class="p-3">
                <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
                <p v-if="product.subTitle" class="text-xs text-gray-400 mb-1 line-clamp-1">{{ product.subTitle }}</p>
                <div class="flex items-baseline gap-2">
                  <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.00</span></span>
                </div>
              </div>
            </button>
          </div>
        </div>
      </section>
    </template>
    </template>
  </div>
</template>

<style scoped>
/* 自定义滚动条隐藏 */
.overflow-x-auto::-webkit-scrollbar {
  display: none;
}
.overflow-x-auto {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
