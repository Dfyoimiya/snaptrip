<script setup lang="ts">
/**
 * ============================================
 * 浏览足迹 (MemberHistoryView)
 * 淘宝风格：日期分组 + 方形图片卡片网格 + 勾选批量删除 + 搜索
 * 默认展示最近 6 个月
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBehaviorsAPI, deleteBehaviorsAPI, type BehaviorItem } from '@/apis/behavior'

const router = useRouter()

const loading = ref(false)
const deleting = ref(false)
const allItems = ref<BehaviorItem[]>([])
const selectedIds = ref<Set<string>>(new Set())
const searchKeyword = ref('')

/** 6 个月前的时间戳 */
const sixMonthsAgo = new Date()
sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6)

/** 过滤 6 个月内，当天去重保留最新时间，按日期分组 */
const groupedByDate = computed(() => {
  const filtered = allItems.value.filter(item => {
    if (!item.createdAt) return false
    if (new Date(item.createdAt) < sixMonthsAgo) return false
    // 搜索过滤
    if (searchKeyword.value.trim()) {
      const kw = searchKeyword.value.trim().toLowerCase()
      const name = (item.productName || '').toLowerCase()
      if (!name.includes(kw)) return false
    }
    return true
  })

  // 按日期 -> itemId 去重，保留每个产品当天的最新浏览
  const dateItemMap = new Map<string, Map<string, BehaviorItem>>()
  for (const item of filtered) {
    const dateKey = item.createdAt!.split('T')[0]
    const itemKey = item.itemId || '__no_id__'
    if (!dateItemMap.has(dateKey)) dateItemMap.set(dateKey, new Map())
    const itemMap = dateItemMap.get(dateKey)!
    const existing = itemMap.get(itemKey)
    if (!existing || item.createdAt! > existing.createdAt!) {
      itemMap.set(itemKey, item)
    }
  }

  return Array.from(dateItemMap.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([dateKey, itemMap]) => ({
      label: formatDateLabel(dateKey),
      items: Array.from(itemMap.values()).sort(
        (a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''),
      ),
    }))
})

/** 所有可见 item 的 id 集合 */
const visibleIds = computed(() => {
  const ids = new Set<string>()
  for (const g of groupedByDate.value) {
    for (const item of g.items) ids.add(item.id)
  }
  return ids
})

const totalCount = computed(() => visibleIds.value.size)

const isAllSelected = computed(() => {
  if (totalCount.value === 0) return false
  return visibleIds.value.size > 0 && [...visibleIds.value].every(id => selectedIds.value.has(id))
})

const isIndeterminate = computed(() => {
  if (selectedIds.value.size === 0) return false
  return !isAllSelected.value
})

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const m = d.getMonth() + 1
  const day = d.getDate()
  const label = `${m}月${day}日`
  if (dateStr === today.toISOString().split('T')[0]) return `今天 ${label}`
  if (dateStr === yesterday.toISOString().split('T')[0]) return `昨天 ${label}`
  return label
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await getBehaviorsAPI('view', 1, 200)
    allItems.value = res.items || []
    selectedIds.value.clear()
  } catch (err: any) {
    console.error('加载浏览历史失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

// ── 选择操作 ──

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(visibleIds.value)
  }
}

async function batchDelete() {
  if (selectedIds.value.size === 0 || deleting.value) return
  if (!confirm(`确认删除选中的 ${selectedIds.value.size} 条浏览记录？`)) return
  deleting.value = true
  try {
    const ids = [...selectedIds.value].join(',')
    await deleteBehaviorsAPI(undefined, ids)
    // 从本地移除已删除的
    const removed = selectedIds.value
    allItems.value = allItems.value.filter(item => !removed.has(item.id))
    selectedIds.value = new Set()
  } catch (err: any) {
    console.error('删除失败:', err?.message || err)
  } finally {
    deleting.value = false
  }
}

async function clearAllHistory() {
  if (deleting.value) return
  if (!confirm('确认清空全部浏览记录？此操作不可撤销。')) return
  deleting.value = true
  try {
    await deleteBehaviorsAPI('view')
    allItems.value = []
    selectedIds.value = new Set()
  } catch (err: any) {
    console.error('清空失败:', err?.message || err)
  } finally {
    deleting.value = false
  }
}

// ── 导航 ──

function goProduct(id: string | null) {
  if (!id) return
  router.push(`/product/${id}`)
}

const formatPrice = (p: number | null) => {
  if (p == null) return ''
  return p.toLocaleString('zh-CN')
}

onMounted(loadHistory)
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
      <h2 class="text-lg font-bold text-gray-900 flex-shrink-0">浏览足迹</h2>

      <!-- 全选 + 操作 + 搜索 -->
      <div v-if="allItems.length > 0" class="flex items-center gap-3 flex-1 justify-end">
        <label class="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer select-none hover:text-gray-700 flex-shrink-0">
          <input
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            :indeterminate="isIndeterminate"
            :checked="isAllSelected"
            @change="toggleSelectAll"
          />
          全选
        </label>

        <button
          v-if="selectedIds.size > 0"
          :disabled="deleting"
          class="px-3 py-1.5 text-xs bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors disabled:opacity-50 flex-shrink-0"
          @click="batchDelete"
        >{{ deleting ? '删除中...' : `删除(${selectedIds.size})` }}</button>

        <button
          v-else-if="totalCount > 0"
          :disabled="deleting"
          class="px-3 py-1.5 text-xs border border-red-200 text-red-500 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50 flex-shrink-0"
          @click="clearAllHistory"
        >清空全部</button>

        <span class="text-xs text-gray-300">|</span>

        <div class="relative w-44">
          <svg xmlns="http://www.w3.org/2000/svg" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索浏览记录"
            class="w-full h-8 pl-8 pr-3 border border-gray-200 rounded-md text-xs focus:outline-none focus:border-brand-400"
          />
        </div>
      </div>

      <div v-else class="text-xs text-gray-400 flex-shrink-0">共 0 件</div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-20 text-gray-400">
      <svg class="animate-spin h-6 w-6 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      加载中...
    </div>

    <!-- 空状态 -->
    <div v-else-if="allItems.length === 0" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-base font-medium">暂无浏览记录</p>
      <p class="text-sm mt-1">开始浏览商品，您的足迹会出现在这里</p>
      <button class="mt-4 px-6 py-2 bg-brand-600 text-white text-sm rounded-lg hover:bg-brand-700 transition-colors" @click="router.push('/')">去逛逛</button>
    </div>

    <!-- 搜索无结果 -->
    <div v-else-if="totalCount === 0" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <p>未找到 "{{ searchKeyword }}" 的相关记录</p>
    </div>

    <!-- 按日期分组的商品网格 -->
    <div v-else class="px-6 py-4 space-y-8">
      <div v-for="group in groupedByDate" :key="group.label">
        <!-- 日期标题 -->
        <div class="flex items-center gap-3 mb-4">
          <h3 class="text-base font-bold text-gray-800">{{ group.label }}</h3>
          <span class="text-xs text-gray-400">{{ group.items.length }} 件</span>
        </div>

        <!-- 商品网格 -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <div
            v-for="item in group.items"
            :key="item.id"
            class="group relative cursor-pointer"
            @click="goProduct(item.itemId)"
          >
            <!-- 方形图片 -->
            <div class="aspect-square bg-gray-50 rounded-xl overflow-hidden relative">
              <img
                v-if="item.productPic"
                :src="item.productPic"
                :alt="item.productName || ''"
                class="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
              />
              <div v-else class="w-full h-full flex items-center justify-center text-gray-300">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>

              <!-- 左上角勾选框（常驻） -->
              <label
                class="absolute top-2 left-2 z-10"
                @click.stop
              >
                <input
                  type="checkbox"
                  :checked="selectedIds.has(item.id)"
                  class="peer sr-only"
                  @change="toggleSelect(item.id)"
                />
                <div class="w-5 h-5 rounded border-2 border-white/80 bg-black/20 peer-checked:bg-brand-600 peer-checked:border-brand-600 flex items-center justify-center transition-colors cursor-pointer hover:bg-black/30">
                  <svg v-if="selectedIds.has(item.id)" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </label>
            </div>

            <!-- 文字简介 -->
            <div class="pt-2">
              <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] group-hover:text-brand-600 transition-colors">
                {{ item.productName || '已下架商品' }}
              </p>
              <div class="flex items-baseline gap-2 mt-1">
                <span v-if="item.productPrice != null" class="text-brand-600 font-bold text-sm">
                  <span class="text-xs">&yen;</span>{{ formatPrice(item.productPrice) }}
                </span>
                <span v-else class="text-xs text-gray-300">已下架</span>
              </div>
            </div>
          </div>
        </div>
      </div>
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
/* Hide native checkbox but keep accessible; show custom styled box */
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border-width: 0;
}
</style>
