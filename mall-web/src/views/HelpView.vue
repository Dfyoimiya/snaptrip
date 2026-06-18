<script setup lang="ts">
/**
 * ============================================
 * 帮助中心页面 —— 动态加载后端帮助数据
 * ============================================
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getNoticeListAPI } from '@/apis/notice'

const router = useRouter()

interface HelpItem {
  id: string
  title: string
  content: string
  categoryName: string
}

const helps = ref<HelpItem[]>([])
const loading = ref(false)
const selectedCategory = ref('')
const selectedHelp = ref<HelpItem | null>(null)

const categories = computed(() => {
  const set = new Set(helps.value.map(h => h.categoryName).filter(Boolean))
  return Array.from(set).sort()
})

const filteredHelps = computed(() => {
  if (!selectedCategory.value) return helps.value
  return helps.value.filter(h => h.categoryName === selectedCategory.value)
})

onMounted(async () => {
  loading.value = true
  try {
    const data = await getNoticeListAPI({ page: 1, page_size: 100 })
    helps.value = ((data as any).items || []) as HelpItem[]
  } catch {
    helps.value = []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="help-page max-w-4xl mx-auto">
    <!-- 页面标题 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4 mb-5">
      <div class="flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h1 class="text-xl font-bold text-gray-900">帮助中心</h1>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div v-if="categories.length" class="flex flex-wrap gap-2 mb-5">
      <button
        class="px-4 py-1.5 rounded-full text-sm transition-colors"
        :class="selectedCategory === '' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        @click="selectedCategory = ''; selectedHelp = null"
      >
        全部
      </button>
      <button
        v-for="cat in categories"
        :key="cat"
        class="px-4 py-1.5 rounded-full text-sm transition-colors"
        :class="selectedCategory === cat ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        @click="selectedCategory = cat; selectedHelp = null"
      >
        {{ cat }}
      </button>
    </div>

    <div class="flex gap-5">
      <!-- 左侧列表 -->
      <div class="flex-1 min-w-0">
        <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
          加载中...
        </div>

        <div v-else-if="filteredHelps.length" class="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50">
          <div
            v-for="help in filteredHelps"
            :key="help.id"
            class="px-6 py-4 hover:bg-gray-50/30 transition-colors cursor-pointer"
            :class="{ 'bg-brand-50/50 border-l-4 border-brand-500': selectedHelp?.id === help.id }"
            @click="selectedHelp = help"
          >
            <div class="flex items-center gap-3">
              <span v-if="help.categoryName" class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded flex-shrink-0">{{ help.categoryName }}</span>
              <span class="text-sm font-medium text-gray-900 truncate">{{ help.title }}</span>
            </div>
          </div>
        </div>

        <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
          暂无帮助内容
        </div>
      </div>

      <!-- 右侧详情 -->
      <div class="w-96 flex-shrink-0">
        <div v-if="selectedHelp" class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 sticky top-6">
          <h2 class="text-lg font-bold text-gray-900 mb-4">{{ selectedHelp.title }}</h2>
          <div class="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-line">
            {{ selectedHelp.content || '暂无详细内容' }}
          </div>
        </div>
        <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-center text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto mb-2 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
          </svg>
          <p class="text-sm">选择左侧帮助项目查看详情</p>
        </div>
      </div>
    </div>

    <!-- 返回顶部 / 更多帮助 -->
    <div class="mt-8 pt-6 border-t border-gray-100 text-center">
      <p class="text-sm text-gray-400 mb-3">没有找到答案？</p>
      <button
        class="text-sm text-brand-600 hover:text-brand-700 font-medium underline underline-offset-2"
        @click="router.push('/notice')"
      >
        查看商城公告
      </button>
    </div>
  </div>
</template>
