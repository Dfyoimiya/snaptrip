<script setup lang="ts">
/**
 * ============================================
 * 商城公告列表页 (NoticeListView)
 * 简洁的新闻列表页
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Notice {
  id: number
  title: string
  category: string
  publishTime: string
  isTop: boolean
  isNew: boolean
  summary: string
}

const notices = ref<Notice[]>([
  { id: 1, title: '关于618年中大促活动规则调整的通知', category: '活动公告', publishTime: '2026-06-08', isTop: true, isNew: true, summary: '为更好地服务广大消费者，618年中大促部分活动规则进行调整，请各位用户仔细阅读。' },
  { id: 2, title: '物流配送时效调整公告', category: '服务公告', publishTime: '2026-06-07', isTop: true, isNew: false, summary: '因受天气影响，部分地区的物流配送时效将有所调整，给您带来不便敬请谅解。' },
  { id: 3, title: '新增支付方式——微信支付上线', category: '功能更新', publishTime: '2026-06-06', isTop: false, isNew: true, summary: '商城已正式上线微信支付功能，支持微信扫码支付和微信支付分付款。' },
  { id: 4, title: '2026年夏季售后服务升级', category: '服务公告', publishTime: '2026-06-05', isTop: false, isNew: false, summary: '为进一步提升用户体验，我们对售后服务体系进行了全面升级，新增上门取件和极速退款服务。' },
  { id: 5, title: '会员积分体系全新改版', category: '功能更新', publishTime: '2026-06-04', isTop: false, isNew: false, summary: '会员积分体系已全新改版，新增积分兑换、积分抽奖等多种玩法，快来体验吧！' },
  { id: 6, title: '关于防范钓鱼网站的提醒公告', category: '安全公告', publishTime: '2026-06-03', isTop: false, isNew: false, summary: '近期发现有不法分子仿冒本商城网站进行诈骗活动，请广大用户提高警惕，认准官方域名。' },
  { id: 7, title: '618品牌特卖专区预告', category: '活动公告', publishTime: '2026-06-02', isTop: false, isNew: false, summary: '618品牌特卖专区即将开启，Apple、华为、Dyson等大牌商品低至5折起！' },
  { id: 8, title: '系统维护通知', category: '服务公告', publishTime: '2026-06-01', isTop: false, isNew: false, summary: '商城将于6月10日凌晨2:00-4:00进行系统维护，期间部分功能可能暂时无法使用。' },
])

/** 分类筛选 */
const activeCategory = ref('all')
const categories = [{ key: 'all', label: '全部' }, { key: '活动公告', label: '活动' }, { key: '服务公告', label: '服务' }, { key: '功能更新', label: '更新' }, { key: '安全公告', label: '安全' }]

/** 分页 */
const currentPage = ref(1)
const pageSize = 5

const filteredNotices = computed(() => {
  if (activeCategory.value === 'all') return notices.value
  return notices.value.filter(n => n.category === activeCategory.value)
})

const totalPages = computed(() => Math.ceil(filteredNotices.value.length / pageSize))
const paginatedNotices = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredNotices.value.slice(start, start + pageSize)
})
</script>

<template>
  <div class="notice-list-page space-y-5">
    <!-- 页面标题 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-bold text-gray-900 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
          </svg>
          商城公告
        </h1>
        <span class="text-sm text-gray-400">共 {{ filteredNotices.length }} 条公告</span>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div class="flex items-center gap-2">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['px-4 py-2 text-sm rounded-lg transition-colors', activeCategory === cat.key ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100']"
          @click="activeCategory = cat.key; currentPage = 1"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- 公告列表 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50">
      <div
        v-for="notice in paginatedNotices"
        :key="notice.id"
        class="px-6 py-5 hover:bg-gray-50/30 transition-colors cursor-pointer"
        @click="router.push(`/notice/${notice.id}`)"
      >
        <div class="flex items-start gap-4">
          <!-- 左侧标记 -->
          <div class="flex items-center gap-2 flex-shrink-0 mt-0.5">
            <span v-if="notice.isTop" class="bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">置顶</span>
            <span v-if="notice.isNew" class="bg-orange-500 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">NEW</span>
            <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{{ notice.category }}</span>
          </div>
          <!-- 内容 -->
          <div class="flex-1 min-w-0">
            <h3 class="text-sm font-medium text-gray-900 hover:text-red-600 transition-colors mb-1">{{ notice.title }}</h3>
            <p class="text-xs text-gray-400 line-clamp-1">{{ notice.summary }}</p>
          </div>
          <!-- 时间 -->
          <span class="text-xs text-gray-400 flex-shrink-0">{{ notice.publishTime }}</span>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-2">
      <button class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30" :disabled="currentPage === 1" @click="currentPage--">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <button v-for="page in totalPages" :key="page" :class="['min-w-9 h-9 flex items-center justify-center rounded-md text-sm', currentPage === page ? 'bg-red-600 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50']" @click="currentPage = page">
        {{ page }}
      </button>
      <button class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30" :disabled="currentPage === totalPages" @click="currentPage++">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" /></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-1 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
