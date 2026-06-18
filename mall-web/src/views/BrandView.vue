<script setup lang="ts">
/**
 * ============================================
 * 品牌专区页 (BrandView)
 * PC 端品牌 Logo 墙 + A-Z 字母索引
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBrandRecommendListAPI } from '@/apis/brand'
import type { PmsBrand } from '@/types/brand'

const router = useRouter()

const loading = ref(false)
const brands = ref<PmsBrand[]>([])

async function loadBrands() {
  loading.value = true
  try {
    const res = await getBrandRecommendListAPI({ page: 1, page_size: 100 })
    brands.value = res.items || []
  } catch (err: any) {
    console.error('加载品牌列表失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

/** A-Z 字母表 */
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

/** 当前选中的字母 */
const activeLetter = ref('')

/** 按字母分组的品牌 */
const groupedBrands = computed(() => {
  const groups: Record<string, PmsBrand[]> = {}
  const source = activeLetter.value
    ? brands.value.filter(b => b.firstLetter === activeLetter.value)
    : brands.value

  source.forEach(brand => {
    const letter = brand.firstLetter
    if (!groups[letter]) groups[letter] = []
    groups[letter].push(brand)
  })

  // 按字母排序
  return Object.keys(groups).sort().reduce((acc, key) => {
    acc[key] = groups[key] || []
    return acc
  }, {} as Record<string, PmsBrand[]>)
})

/** 热门品牌（按商品数量排序，前8） */
const hotBrands = computed(() =>
  [...brands.value].sort((a, b) => (b.productCount || 0) - (a.productCount || 0)).slice(0, 8)
)

onMounted(() => {
  loadBrands()
})
</script>

<template>
  <div class="brand-page space-y-5">
    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <template v-else>
    <!-- ====== 热门品牌 ====== -->
    <div v-if="hotBrands.length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 class="text-base font-bold text-gray-900 mb-4">热门品牌</h2>
      <div class="grid grid-cols-8 gap-4">
        <button
          v-for="brand in hotBrands"
          :key="brand.id"
          class="group flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-md transition-all"
          @click="router.push(`/brand/${brand.id}`)"
        >
          <div class="w-14 h-14 rounded-full bg-gray-50 overflow-hidden flex items-center justify-center">
            <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover group-hover:scale-110 transition-transform" />
          </div>
          <span class="text-xs text-gray-700 text-center truncate w-full">{{ brand.name.split(' ')[0] }}</span>
        </button>
      </div>
    </div>

    <!-- ====== 品牌 Logo 墙 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <!-- A-Z 字母索引 -->
      <div class="flex items-center gap-1 px-6 py-3 border-b border-gray-100 overflow-x-auto">
        <button
          :class="[
            'px-3 py-1.5 text-sm rounded-md transition-colors flex-shrink-0',
            activeLetter === '' ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100',
          ]"
          @click="activeLetter = ''"
        >
          全部
        </button>
        <button
          v-for="letter in letters"
          :key="letter"
          :class="[
            'w-9 h-9 flex items-center justify-center text-sm rounded-md transition-colors flex-shrink-0',
            activeLetter === letter
              ? 'bg-red-600 text-white font-medium'
              : 'text-gray-600 hover:bg-gray-100',
          ]"
          @click="activeLetter = activeLetter === letter ? '' : letter"
        >
          {{ letter }}
        </button>
      </div>

      <!-- 品牌分组列表 -->
      <div class="p-6 space-y-6">
        <div
          v-for="(group, letter) in groupedBrands"
          :key="letter"
          class="flex items-start gap-4"
        >
          <!-- 字母标识 -->
          <div class="w-10 h-10 rounded-lg bg-red-600 flex items-center justify-center flex-shrink-0">
            <span class="text-lg font-bold text-white">{{ letter }}</span>
          </div>

          <!-- 品牌网格 -->
          <div class="flex-1 grid grid-cols-6 gap-3">
            <button
              v-for="brand in group"
              :key="brand.id"
              class="group flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-sm transition-all text-left"
              @click="router.push(`/brand/${brand.id}`)"
            >
              <div class="w-10 h-10 rounded bg-gray-50 overflow-hidden flex-shrink-0">
                <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm text-gray-800 truncate group-hover:text-red-600 transition-colors">{{ brand.name }}</p>
                <p class="text-xs text-gray-400">{{ brand.productCount }} 件商品</p>
              </div>
            </button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="Object.keys(groupedBrands).length === 0" class="text-center py-10 text-gray-400">
          暂无该字母开头的品牌
        </div>
      </div>
    </div>
    </template>
  </div>
</template>
