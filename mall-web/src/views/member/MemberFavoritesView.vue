<script setup lang="ts">
/**
 * ============================================
 * 我的收藏页 (MemberFavoritesView)
 * 支持批量选中、删除操作的网格图片列表
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface FavoriteItem {
  id: number
  name: string
  price: number
  originalPrice: number
  pic: string
  addedTime: string
  brand: string
}

const favorites = ref<FavoriteItem[]>([
  { id: 101, name: 'Apple MacBook Air M3 16+512G', price: 9999, originalPrice: 11999, pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', addedTime: '2026-06-01', brand: 'Apple' },
  { id: 102, name: 'Dyson Supersonic HD15 吹风机', price: 2590, originalPrice: 3290, pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', addedTime: '2026-06-02', brand: 'Dyson' },
  { id: 104, name: 'Nike Air Force 1 经典板鞋', price: 749, originalPrice: 899, pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop', addedTime: '2026-06-03', brand: 'Nike' },
  { id: 103, name: 'SK-II 神仙水 230ml', price: 1540, originalPrice: 2150, pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=300&h=300&fit=crop', addedTime: '2026-06-04', brand: 'SK-II' },
  { id: 201, name: '华为 Mate 60 Pro+ 16GB+512GB', price: 8999, originalPrice: 9999, pic: 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=300&h=300&fit=crop', addedTime: '2026-06-05', brand: '华为' },
  { id: 205, name: 'Anker 737 240W 氮化镓充电器', price: 399, originalPrice: 599, pic: 'https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=300&h=300&fit=crop', addedTime: '2026-06-06', brand: 'Anker' },
])

/** 批量选中模式 */
const batchMode = ref(false)
/** 选中的 ID */
const selectedIds = ref<Set<number>>(new Set())

/** 是否全选 */
const isAllSelected = computed(() => favorites.value.length > 0 && favorites.value.every(f => selectedIds.value.has(f.id)))

/** 切换批量模式 */
const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (!batchMode.value) selectedIds.value.clear()
}

/** 切换选中 */
const toggleSelect = (id: number) => {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

/** 全选/取消全选 */
const toggleSelectAll = () => {
  if (isAllSelected.value) selectedIds.value.clear()
  else favorites.value.forEach(f => selectedIds.value.add(f.id))
}

/** 批量删除 */
const batchDelete = () => {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 件商品吗？`)) return
  favorites.value = favorites.value.filter(f => !selectedIds.value.has(f.id))
  selectedIds.value.clear()
  if (favorites.value.length === 0) batchMode.value = false
}

/** 单个删除 */
const removeItem = (id: number) => {
  favorites.value = favorites.value.filter(f => f.id !== id)
}
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
            <input type="checkbox" :checked="isAllSelected" class="rounded border-gray-300 text-red-600 focus:ring-red-500" @change="toggleSelectAll" />
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
        <button v-else class="text-sm text-gray-500 hover:text-red-600 px-3 py-1.5 border border-gray-200 rounded-lg hover:border-red-300 transition-colors" @click="toggleBatchMode">
          批量管理
        </button>
      </div>
    </div>

    <!-- 收藏网格 -->
    <div v-if="favorites.length" class="p-5 grid grid-cols-4 gap-4">
      <div
        v-for="item in favorites"
        :key="item.id"
        class="group relative rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-md transition-all overflow-hidden"
        :class="{ 'ring-2 ring-red-500': batchMode && selectedIds.has(item.id) }"
      >
        <!-- 批量选择复选框 -->
        <div v-if="batchMode" class="absolute top-2 left-2 z-20">
          <input
            type="checkbox"
            :checked="selectedIds.has(item.id)"
            class="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer"
            @click.stop="toggleSelect(item.id)"
          />
        </div>

        <!-- 删除按钮（非批量模式） -->
        <button
          v-if="!batchMode"
          class="absolute top-2 right-2 z-20 w-7 h-7 bg-white/80 backdrop-blur rounded-full flex items-center justify-center text-gray-400 hover:text-red-600 hover:bg-white transition-all opacity-0 group-hover:opacity-100"
          @click.stop="removeItem(item.id)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- 商品卡片 -->
        <button class="w-full text-left" @click="!batchMode && router.push(`/product/${item.id}`)">
          <div class="aspect-square bg-gray-50 overflow-hidden">
            <img :src="item.pic" :alt="item.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform" />
          </div>
          <div class="p-3">
            <p class="text-sm text-gray-800 line-clamp-2 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ item.name }}</p>
            <div class="flex items-baseline gap-2">
              <span class="text-red-600 font-bold">&yen;{{ item.price }}</span>
              <span class="text-xs text-gray-400 line-through">&yen;{{ item.originalPrice }}</span>
            </div>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-xs text-gray-400">{{ item.brand }}</span>
              <span class="text-xs text-gray-400">{{ item.addedTime }}</span>
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
      <button class="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors" @click="router.push('/')">
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
