<script setup lang="ts">
/**
 * ============================================
 * 品牌专区页 (BrandView)
 * PC 端品牌 Logo 墙 + A-Z 字母索引
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/** 品牌数据结构 */
interface BrandItem {
  id: number
  name: string
  firstLetter: string
  logo: string
  productCount: number
}

/** Mock 品牌数据 */
const brands = ref<BrandItem[]>([
  { id: 1, name: 'Apple', firstLetter: 'A', logo: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=200&h=200&fit=crop', productCount: 156 },
  { id: 2, name: '华为 HUAWEI', firstLetter: 'H', logo: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=200&h=200&fit=crop', productCount: 328 },
  { id: 3, name: '小米 Xiaomi', firstLetter: 'X', logo: 'https://images.unsplash.com/photo-1567581935884-3349723552ca?w=200&h=200&fit=crop', productCount: 512 },
  { id: 4, name: 'Nike', firstLetter: 'N', logo: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop', productCount: 892 },
  { id: 5, name: 'Adidas', firstLetter: 'A', logo: 'https://images.unsplash.com/photo-1584735175315-9d5df23860e6?w=200&h=200&fit=crop', productCount: 756 },
  { id: 6, name: 'Sony', firstLetter: 'S', logo: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=200&h=200&fit=crop', productCount: 198 },
  { id: 7, name: 'Dyson', firstLetter: 'D', logo: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=200&h=200&fit=crop', productCount: 45 },
  { id: 8, name: '三星 SAMSUNG', firstLetter: 'S', logo: 'https://images.unsplash.com/photo-1610945265064-f4d215f72119?w=200&h=200&fit=crop', productCount: 267 },
  { id: 9, name: '联想 Lenovo', firstLetter: 'L', logo: 'https://images.unsplash.com/photo-1588872657578-7efd1f1555b3?w=200&h=200&fit=crop', productCount: 189 },
  { id: 10, name: '海尔 Haier', firstLetter: 'H', logo: 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=200&h=200&fit=crop', productCount: 423 },
  { id: 11, name: '美的 Midea', firstLetter: 'M', logo: 'https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=200&h=200&fit=crop', productCount: 567 },
  { id: 12, name: 'Nintendo', firstLetter: 'N', logo: 'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=200&h=200&fit=crop', productCount: 78 },
  { id: 13, name: 'Canon', firstLetter: 'C', logo: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=200&h=200&fit=crop', productCount: 134 },
  { id: 14, name: 'SK-II', firstLetter: 'S', logo: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=200&h=200&fit=crop', productCount: 56 },
  { id: 15, name: 'Bose', firstLetter: 'B', logo: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&h=200&fit=crop', productCount: 67 },
  { id: 16, name: 'Puma', firstLetter: 'P', logo: 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=200&h=200&fit=crop', productCount: 345 },
  { id: 17, name: '雅诗兰黛', firstLetter: 'Y', logo: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=200&h=200&fit=crop', productCount: 89 },
  { id: 18, name: 'LG', firstLetter: 'L', logo: 'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=200&h=200&fit=crop', productCount: 156 },
  { id: 19, name: 'Philips', firstLetter: 'P', logo: 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=200&h=200&fit=crop', productCount: 234 },
  { id: 20, name: 'DJI 大疆', firstLetter: 'D', logo: 'https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=200&h=200&fit=crop', productCount: 34 },
  { id: 21, name: 'New Balance', firstLetter: 'N', logo: 'https://images.unsplash.com/photo-1539185441755-769473a23570?w=200&h=200&fit=crop', productCount: 278 },
  { id: 22, name: 'Under Armour', firstLetter: 'U', logo: 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=200&h=200&fit=crop', productCount: 189 },
  { id: 23, name: 'Gucci', firstLetter: 'G', logo: 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=200&h=200&fit=crop', productCount: 123 },
  { id: 24, name: 'Zara', firstLetter: 'Z', logo: 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=200&h=200&fit=crop', productCount: 567 },
])

/** A-Z 字母表 */
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

/** 当前选中的字母 */
const activeLetter = ref('')

/** 按字母分组的品牌 */
const groupedBrands = computed(() => {
  const groups: Record<string, BrandItem[]> = {}
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
    acc[key] = groups[key]
    return acc
  }, {} as Record<string, BrandItem[]>)
})

/** 热门品牌（销量前8） */
const hotBrands = computed(() => brands.value.slice(0, 8))
</script>

<template>
  <div class="brand-page space-y-5">
    <!-- ====== 热门品牌 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
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
  </div>
</template>
