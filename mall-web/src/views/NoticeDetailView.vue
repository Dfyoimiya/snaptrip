<script setup lang="ts">
/**
 * ============================================
 * 公告详情页 (NoticeDetailView)
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNoticeDetailAPI } from '@/apis/notice'

const route = useRoute()
const router = useRouter()
const noticeId = route.params.id as string

interface NoticeDetail {
  id: string
  title: string
  content: string
  categoryName: string
  createdAt: string
}

const notice = ref<NoticeDetail | null>(null)
const loading = ref(false)

onMounted(async () => {
  if (!noticeId) return
  loading.value = true
  try {
    notice.value = await getNoticeDetailAPI(noticeId) as unknown as NoticeDetail
  } catch {
    notice.value = null
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="notice-detail-page max-w-3xl mx-auto">
    <!-- 面包屑 -->
    <nav class="flex items-center gap-2 text-sm text-gray-500 mb-4">
      <button class="hover:text-red-600" @click="router.push('/notice')">商城公告</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-900">详情</span>
    </nav>

    <!-- 详情卡片 -->
    <div v-if="notice" class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
      <div class="text-center mb-6 pb-6 border-b border-gray-100">
        <h1 class="text-xl font-bold text-gray-900 mb-3">{{ notice.title }}</h1>
        <div class="flex items-center justify-center gap-3 text-sm text-gray-400">
          <span v-if="notice.categoryName" class="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">{{ notice.categoryName }}</span>
          <span>{{ notice.createdAt }}</span>
        </div>
      </div>

      <div class="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-line">
        {{ notice.content }}
      </div>

      <div class="mt-8 pt-6 border-t border-gray-100 flex items-center justify-between">
        <button class="text-sm text-gray-500 hover:text-red-600 flex items-center gap-1" @click="router.push('/notice')">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          返回列表
        </button>
        <span class="text-xs text-gray-400">Mall PC Web 商城运营团队</span>
      </div>
    </div>

    <div v-else-if="!loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      公告不存在或已下架
    </div>
  </div>
</template>
