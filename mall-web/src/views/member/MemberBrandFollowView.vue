<script setup lang="ts">
/**
 * ============================================
 * 品牌关注页 (MemberBrandFollowView)
 * 支持批量选中、取消关注
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface BrandFollow {
  id: number
  name: string
  logo: string
  productCount: number
  followedTime: string
}

const brands = ref<BrandFollow[]>([
  { id: 1, name: 'Apple', logo: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=200&h=200&fit=crop', productCount: 156, followedTime: '2026-05-15' },
  { id: 4, name: 'Nike', logo: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop', productCount: 892, followedTime: '2026-05-20' },
  { id: 7, name: 'Dyson', logo: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=200&h=200&fit=crop', productCount: 45, followedTime: '2026-05-28' },
  { id: 2, name: '华为', logo: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=200&h=200&fit=crop', productCount: 328, followedTime: '2026-06-01' },
  { id: 6, name: 'Sony', logo: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=200&h=200&fit=crop', productCount: 198, followedTime: '2026-06-03' },
])

const batchMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const isAllSelected = computed(() => brands.value.length > 0 && brands.value.every(b => selectedIds.value.has(b.id)))

const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (!batchMode.value) selectedIds.value.clear()
}
const toggleSelect = (id: number) => { selectedIds.value.has(id) ? selectedIds.value.delete(id) : selectedIds.value.add(id) }
const toggleSelectAll = () => { isAllSelected.value ? selectedIds.value.clear() : brands.value.forEach(b => selectedIds.value.add(b.id)) }
const batchUnfollow = () => {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定取消关注选中的 ${selectedIds.value.size} 个品牌吗？`)) return
  brands.value = brands.value.filter(b => !selectedIds.value.has(b.id))
  selectedIds.value.clear()
  if (brands.value.length === 0) batchMode.value = false
}
const unfollow = (id: number) => { brands.value = brands.value.filter(b => b.id !== id) }
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-bold text-gray-900">品牌关注</h2>
        <span class="text-sm text-gray-400">已关注 {{ brands.length }} 个品牌</span>
      </div>
      <div class="flex items-center gap-2">
        <template v-if="batchMode">
          <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer mr-2">
            <input type="checkbox" :checked="isAllSelected" class="rounded border-gray-300 text-red-600" @change="toggleSelectAll" />
            全选
          </label>
          <button v-if="selectedIds.size > 0" class="text-sm text-red-600 px-3 py-1.5 bg-red-50 rounded-lg" @click="batchUnfollow">
            取消关注({{ selectedIds.size }})
          </button>
          <button class="text-sm text-gray-500 px-3 py-1.5" @click="toggleBatchMode">完成</button>
        </template>
        <button v-else class="text-sm text-gray-500 hover:text-red-600 px-3 py-1.5 border border-gray-200 rounded-lg" @click="toggleBatchMode">
          批量管理
        </button>
      </div>
    </div>

    <div v-if="brands.length" class="p-5 grid grid-cols-4 gap-4">
      <div
        v-for="brand in brands"
        :key="brand.id"
        class="group relative flex flex-col items-center p-5 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-md transition-all bg-white"
        :class="{ 'ring-2 ring-red-500': batchMode && selectedIds.has(brand.id) }"
      >
        <div v-if="batchMode" class="absolute top-2 left-2">
          <input type="checkbox" :checked="selectedIds.has(brand.id)" class="w-5 h-5 rounded border-gray-300 text-red-600" @click.stop="toggleSelect(brand.id)" />
        </div>
        <button v-if="!batchMode" class="absolute top-2 right-2 w-7 h-7 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all" @click.stop="unfollow(brand.id)">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
        <button class="flex flex-col items-center gap-2 w-full" @click="!batchMode && router.push(`/brand/${brand.id}`)">
          <div class="w-16 h-16 rounded-full bg-gray-50 overflow-hidden border border-gray-100">
            <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover" />
          </div>
          <span class="text-sm font-medium text-gray-900">{{ brand.name }}</span>
          <span class="text-xs text-gray-400">{{ brand.productCount }} 件商品</span>
          <span class="text-xs text-gray-300">关注于 {{ brand.followedTime }}</span>
        </button>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.784.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
      </svg>
      <p>暂无关注的品牌</p>
    </div>
  </div>
</template>
