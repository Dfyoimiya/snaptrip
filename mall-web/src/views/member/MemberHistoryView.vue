<script setup lang="ts">
/**
 * ============================================
 * 浏览历史页 (MemberHistoryView)
 * 支持批量选中、删除操作的网格图片列表
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface HistoryItem {
  id: number
  name: string
  price: number
  pic: string
  viewTime: string
  brand: string
}

const historyList = ref<HistoryItem[]>([
  { id: 101, name: 'Apple MacBook Air M3 16+512G', price: 9999, pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', viewTime: '今天 14:32', brand: 'Apple' },
  { id: 104, name: 'Nike Air Force 1 经典板鞋', price: 749, pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop', viewTime: '今天 11:15', brand: 'Nike' },
  { id: 103, name: 'SK-II 神仙水 230ml', price: 1540, pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=300&h=300&fit=crop', viewTime: '昨天 20:08', brand: 'SK-II' },
  { id: 102, name: 'Dyson Supersonic HD15 吹风机', price: 2590, pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', viewTime: '昨天 16:45', brand: 'Dyson' },
  { id: 105, name: '小米14 Pro 16GB+512GB', price: 5499, pic: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop', viewTime: '前天 09:30', brand: '小米' },
  { id: 106, name: '雅诗兰黛 小棕瓶精华液 50ml', price: 935, pic: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=300&h=300&fit=crop', viewTime: '06-05', brand: '雅诗兰黛' },
  { id: 107, name: 'Sony PS5 光驱版游戏主机', price: 3599, pic: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=300&h=300&fit=crop', viewTime: '06-04', brand: 'Sony' },
  { id: 108, name: 'Nespresso 胶囊咖啡机', price: 866, pic: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=300&h=300&fit=crop', viewTime: '06-03', brand: 'Nespresso' },
])

const batchMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const isAllSelected = computed(() => historyList.value.length > 0 && historyList.value.every(h => selectedIds.value.has(h.id)))

const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (!batchMode.value) selectedIds.value.clear()
}
const toggleSelect = (id: number) => { selectedIds.value.has(id) ? selectedIds.value.delete(id) : selectedIds.value.add(id) }
const toggleSelectAll = () => { isAllSelected.value ? selectedIds.value.clear() : historyList.value.forEach(h => selectedIds.value.add(h.id)) }
const batchDelete = () => {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 条浏览记录吗？`)) return
  historyList.value = historyList.value.filter(h => !selectedIds.value.has(h.id))
  selectedIds.value.clear()
  if (historyList.value.length === 0) batchMode.value = false
}
const clearAll = () => { if (confirm('确定清空所有浏览记录吗？')) { historyList.value = []; batchMode.value = false } }
const removeItem = (id: number) => { historyList.value = historyList.value.filter(h => h.id !== id) }
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-bold text-gray-900">浏览足迹</h2>
        <span class="text-sm text-gray-400">共 {{ historyList.length }} 条</span>
      </div>
      <div class="flex items-center gap-2">
        <template v-if="batchMode">
          <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer mr-2">
            <input type="checkbox" :checked="isAllSelected" class="rounded border-gray-300 text-red-600 focus:ring-red-500" @change="toggleSelectAll" />
            全选
          </label>
          <button v-if="selectedIds.size > 0" class="text-sm text-red-600 hover:text-red-700 px-3 py-1.5 bg-red-50 rounded-lg" @click="batchDelete">
            删除({{ selectedIds.size }})
          </button>
          <button class="text-sm text-gray-500 px-3 py-1.5" @click="toggleBatchMode">完成</button>
        </template>
        <template v-else>
          <button class="text-sm text-gray-500 hover:text-red-600 px-3 py-1.5" @click="clearAll">清空</button>
          <button class="text-sm text-gray-500 hover:text-red-600 px-3 py-1.5 border border-gray-200 rounded-lg" @click="toggleBatchMode">批量管理</button>
        </template>
      </div>
    </div>

    <div v-if="historyList.length" class="p-5 grid grid-cols-4 gap-4">
      <div
        v-for="item in historyList"
        :key="item.id"
        class="group relative rounded-lg border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all overflow-hidden"
        :class="{ 'ring-2 ring-red-500': batchMode && selectedIds.has(item.id) }"
      >
        <div v-if="batchMode" class="absolute top-2 left-2 z-20">
          <input type="checkbox" :checked="selectedIds.has(item.id)" class="w-5 h-5 rounded border-gray-300 text-red-600" @click.stop="toggleSelect(item.id)" />
        </div>
        <button v-if="!batchMode" class="absolute top-2 right-2 z-20 w-7 h-7 bg-white/80 rounded-full flex items-center justify-center text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-all" @click.stop="removeItem(item.id)">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
        <button class="w-full text-left" @click="!batchMode && router.push(`/product/${item.id}`)">
          <div class="aspect-square bg-gray-50 overflow-hidden">
            <img :src="item.pic" :alt="item.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform" />
          </div>
          <div class="p-3">
            <p class="text-sm text-gray-800 line-clamp-2 min-h-[40px] mb-1 group-hover:text-red-600 transition-colors">{{ item.name }}</p>
            <span class="text-red-600 font-bold">&yen;{{ item.price }}</span>
            <div class="flex items-center justify-between mt-1">
              <span class="text-xs text-gray-400">{{ item.brand }}</span>
              <span class="text-xs text-gray-400">{{ item.viewTime }}</span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>暂无浏览记录</p>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
