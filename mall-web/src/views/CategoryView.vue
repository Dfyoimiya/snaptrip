<script setup lang="ts">
/**
 * ============================================
 * 全部分类页 (CategoryView)
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCategoryTreeAPI } from '@/apis/product'
import { getBrandRecommendListAPI } from '@/apis/brand'

const router = useRouter()

interface CategoryNode {
  id: string
  name: string
  icon?: string
  children?: CategoryNode[]
}

const categories = ref<CategoryNode[]>([])
const activeTab = ref(0)
const brandList = ref<{ id: string; name: string }[]>([])
const loading = ref(false)

const currentCategory = computed(() => categories.value[activeTab.value])

const goSearch = (catName: string) => {
  router.push({ path: '/search', query: { keyword: catName } })
}

onMounted(async () => {
  loading.value = true
  try {
    const [tree, brands] = await Promise.all([
      getCategoryTreeAPI(),
      getBrandRecommendListAPI({ page: 1, page_size: 10 }).catch(() => []),
    ])
    categories.value = (tree as CategoryNode[]) || []
    brandList.value = (brands as { id: string; name: string }[]) || []
  } catch {
    // empty
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="category-page space-y-5">
    <!-- 热门品牌 -->
    <div v-if="brandList.length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-base font-bold text-gray-900 mb-3">热门品牌</h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="brand in brandList"
          :key="brand.id"
          class="px-4 py-2 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors"
          @click="router.push(`/brand/${brand.id}`)"
        >
          {{ brand.name }}
        </button>
      </div>
    </div>

    <!-- 分类加载中 -->
    <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      加载中...
    </div>

    <!-- 分类内容 -->
    <template v-else-if="categories.length">
      <!-- 一级分类 Tab -->
      <div class="bg-white rounded-t-xl shadow-sm border border-gray-100 border-b-0">
        <div class="flex overflow-x-auto">
          <button
            v-for="(cat, index) in categories"
            :key="cat.id"
            :class="[
              'flex-shrink-0 px-6 py-4 text-sm font-medium transition-colors border-b-2 whitespace-nowrap',
              activeTab === index
                ? 'text-red-600 border-red-600 bg-red-50/50'
                : 'text-gray-600 border-transparent hover:text-gray-900 hover:bg-gray-50',
            ]"
            @click="activeTab = index"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <!-- 子分类面板 -->
      <div class="bg-white rounded-b-xl shadow-sm border border-gray-100 border-t-0 p-6">
        <div v-if="currentCategory?.children?.length" class="space-y-4">
          <div v-for="(child, idx) in currentCategory.children" :key="idx" class="flex items-start gap-4">
            <div class="w-24 flex-shrink-0 pt-2">
              <span class="text-sm font-bold text-gray-800">{{ child.name }}</span>
            </div>
            <div class="flex-1 flex flex-wrap gap-2">
              <button
                v-for="item in child.children || []"
                :key="item.id"
                class="px-3 py-1.5 text-sm text-gray-600 bg-gray-50 rounded-md hover:bg-red-50 hover:text-red-600 transition-colors"
                @click="goSearch(item.name)"
              >
                {{ item.name }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-10 text-gray-400">
          暂无子分类
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      暂无分类数据
    </div>
  </div>
</template>
