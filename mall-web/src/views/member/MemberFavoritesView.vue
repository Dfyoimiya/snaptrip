<script setup lang="ts">
/**
 * ============================================
 * 我的收藏页 (MemberFavoritesView)
 * 支持批量选中、删除操作的网格图片列表
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchProductCollectionListAPI, deleteProductCollectionAPI } from '@/apis/memberProductCollection'
import type { MemberProductCollection } from '@/types/memberProductCollection'

const router = useRouter()

const loading = ref(false)
const favorites = ref<MemberProductCollection[]>([])

async function loadFavorites() {
  loading.value = true
  try {
    const res = await fetchProductCollectionListAPI({ pageNum: 1, pageSize: 50 })
    favorites.value = (res as unknown as { items: MemberProductCollection[] }).items || []
  } catch (err: any) {
    console.error('加载收藏失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

/** 批量选中模式 */
const batchMode = ref(false)
/** 选中的 productId */
const selectedIds = ref<Set<string>>(new Set())

/** 是否全选 */
const isAllSelected = () => favorites.value.length > 0 && favorites.value.every(f => selectedIds.value.has(f.productId))

/** 切换批量模式 */
const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (!batchMode.value) selectedIds.value.clear()
}

/** 切换选中 */
const toggleSelect = (id: string) => {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

/** 全选/取消全选 */
const toggleSelectAll = () => {
  if (isAllSelected()) selectedIds.value.clear()
  else favorites.value.forEach(f => selectedIds.value.add(f.productId))
}

/** 批量删除 */
const batchDelete = async () => {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 件商品吗？`)) return
  try {
    for (const id of selectedIds.value) {
      await deleteProductCollectionAPI({ productId: String(id) })
    }
    await loadFavorites()
    selectedIds.value.clear()
    if (favorites.value.length === 0) batchMode.value = false
  } catch (err: any) {
    console.error('批量删除失败:', err?.message || err)
  }
}

/** 单个删除 */
const removeItem = async (id: string) => {
  try {
    await deleteProductCollectionAPI({ productId: String(id) })
    await loadFavorites()
  } catch (err: any) {
    console.error('删除收藏失败:', err?.message || err)
  }
}

onMounted(() => {
  loadFavorites()
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <!-- 标题 + 批量操作工具栏 -->
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-bold text-gray-900">我的收藏</h2>
        <span class="text-sm text-gray-400">共 {{ favorites.length }} 件</span>
      </div>
      <div class="flex items-center gap-2">
        <!-- 批量操作按钮 -->
        <template v-if="batchMode">
          <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer mr-2">
            <input type="checkbox" :checked="isAllSelected()" class="rounded border-gray-300 text-brand-600 focus:ring-brand-500" @change="toggleSelectAll" />
            全选
          </label>
          <button
            v-if="selectedIds.size > 0"
            class="text-sm text-red-600 hover:text-red-700 px-3 py-1.5 bg-red-50 rounded-lg transition-colors"
            @click="batchDelete"
          >
            删除选中({{ selectedIds.size }})
          </button>
          <button class="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5" @click="toggleBatchMode">
            完成
          </button>
        </template>
        <button v-else class="text-sm text-gray-500 hover:text-brand-600 px-3 py-1.5 border border-gray-200 rounded-lg hover:border-brand-300 transition-colors" @click="toggleBatchMode">
          批量管理
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- 收藏网格 -->
    <div v-else-if="favorites.length" class="p-5 grid grid-cols-4 gap-4">
      <div
        v-for="item in favorites"
        :key="item.id"
        class="group relative rounded-lg border border-gray-100 hover:border-brand-200 hover:shadow-md transition-all overflow-hidden"
        :class="{ 'ring-2 ring-brand-500': batchMode && selectedIds.has(item.productId) }"
      >
        <!-- 批量选择复选框 -->
        <div v-if="batchMode" class="absolute top-2 left-2 z-20">
          <input
            type="checkbox"
            :checked="selectedIds.has(item.productId)"
            class="w-5 h-5 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
            @click.stop="toggleSelect(item.productId)"
          />
        </div>

        <!-- 删除按钮（非批量模式） -->
        <button
          v-if="!batchMode"
          class="absolute top-2 right-2 z-20 w-7 h-7 bg-white/80 backdrop-blur rounded-full flex items-center justify-center text-gray-400 hover:text-brand-600 hover:bg-white transition-all opacity-0 group-hover:opacity-100"
          @click.stop="removeItem(item.productId)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- 商品卡片 -->
        <button class="w-full text-left" @click="!batchMode && router.push(`/product/${item.productId}`)">
          <div class="aspect-square bg-gray-50 overflow-hidden">
            <img :src="item.productPic" :alt="item.productName" class="w-full h-full object-cover group-hover:scale-105 transition-transform" />
          </div>
          <div class="p-3">
            <p class="text-sm text-gray-800 line-clamp-2 min-h-[40px] mb-2 group-hover:text-brand-600 transition-colors">{{ item.productName }}</p>
            <div class="flex items-baseline gap-2">
              <span class="text-brand-600 font-bold">&yen;{{ item.productPrice }}</span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
      <p>暂无收藏商品</p>
      <button class="mt-4 px-6 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors" @click="router.push('/')">
        去逛逛
      </button>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
