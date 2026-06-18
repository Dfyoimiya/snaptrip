<script setup lang="ts">
/**
 * ============================================
 * 商城公告列表页 (NoticeListView)
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNoticeListAPI } from '@/apis/notice'

const router = useRouter()

interface Notice {
  id: string
  title: string
  categoryName: string
  createdAt: string
}

const notices = ref<Notice[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = 20

onMounted(async () => {
  loading.value = true
  try {
    const data = await getNoticeListAPI({ page: page.value, page_size: pageSize })
    notices.value = (data as any).items || []
    total.value = (data as any).total || 0
  } catch {
    notices.value = []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="notice-list-page space-y-5">
    <!-- 页面标题 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-bold text-gray-900 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
          </svg>
          商城公告
        </h1>
        <span class="text-sm text-gray-400">共 {{ total }} 条公告</span>
      </div>
    </div>

    <!-- 公告列表 -->
    <div v-if="notices.length" class="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50">
      <div
        v-for="notice in notices"
        :key="notice.id"
        class="px-6 py-5 hover:bg-gray-50/30 transition-colors cursor-pointer"
        @click="router.push(`/notice/${notice.id}`)"
      >
        <div class="flex items-start gap-4">
          <div class="flex items-center gap-2 flex-shrink-0 mt-0.5">
            <span v-if="notice.categoryName" class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{{ notice.categoryName }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-sm font-medium text-gray-900 hover:text-brand-600 transition-colors mb-1">{{ notice.title }}</h3>
          </div>
          <span class="text-xs text-gray-400 flex-shrink-0">{{ notice.createdAt }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      暂无公告
    </div>
  </div>
</template>
