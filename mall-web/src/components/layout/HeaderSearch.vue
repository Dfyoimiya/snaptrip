<script setup lang="ts">
/**
 * ============================================
 * 头部搜索区组件 (HeaderSearch)
 * 包含：Logo | 搜索框 (智能下拉) | 购物车入口
 *
 * 下拉面板 3 区:
 *   1. 搜索历史 (localStorage)
 *   2. 热门搜索 (API)
 *   3. AI 推荐 (API, prefix ≥ 2)
 *
 * 键盘导航: ↑↓ 移动高亮, Enter 选中, Esc 关闭
 * 自动补全: 150ms debounce
 * ============================================
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getSearchSuggestAPI, type SuggestSection, type SuggestQuery } from '@/apis/search'
import { trackSearch } from '@/utils/tracker'

const props = defineProps<{
  cartCount: number
}>()

const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

const keyword = ref('')
const showDropdown = ref(false)
const activeIndex = ref(-1)
const loading = ref(false)

// ── 搜索历史 (localStorage) ──
const HISTORY_KEY = '_snaptrip_search_history'
const MAX_HISTORY = 10

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(queries: string[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(queries.slice(0, MAX_HISTORY)))
  } catch { /* quota exceeded — silently ignore */ }
}

function addToHistory(query: string) {
  const history = loadHistory().filter(q => q !== query)
  history.unshift(query)
  saveHistory(history)
}

function removeFromHistory(query: string) {
  saveHistory(loadHistory().filter(q => q !== query))
}

function clearHistory() {
  saveHistory([])
}

// ── API 建议 ──
const sections = ref<SuggestSection[]>([])

let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function fetchSuggestions(prefix: string) {
  loading.value = true
  try {
    const res = await getSearchSuggestAPI({ prefix, limit: 8 })
    sections.value = res.sections || []
  } catch {
    sections.value = []
  } finally {
    loading.value = false
  }
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  const val = keyword.value.trim()
  if (!val) {
    // 空输入: 显示历史 + 热门
    showDropdown.value = true
    sections.value = []
    fetchSuggestions('')
    activeIndex.value = -1
    return
  }
  showDropdown.value = true
  activeIndex.value = -1
  debounceTimer = setTimeout(() => {
    fetchSuggestions(val)
  }, 150)
}

// ── 合并所有建议项 (用于键盘导航) ──
interface FlatItem {
  query: string
  type: string
  sectionIdx: number
}

const flatItems = computed<FlatItem[]>(() => {
  const items: FlatItem[] = []

  // 搜索历史 (本地)
  const history = loadHistory()
  for (const q of history) {
    items.push({ query: q, type: 'history', sectionIdx: -1 })
  }

  // API sections
  for (const s of sections.value) {
    for (const q of s.queries) {
      items.push({ query: q.query, type: q.type, sectionIdx: sections.value.indexOf(s) })
    }
  }
  return items
})

// ── 键盘导航辅助 ──

/** 计算 section 中某个 item 在 flatItems 中的全局索引 */
function getGlobalIndex(section: SuggestSection, itemIdx: number): number {
  const historyLen = keyword.value.trim() ? 0 : loadHistory().length
  let offset = historyLen
  for (const s of sections.value) {
    if (s.section_type === section.section_type) break
    offset += s.queries.length
  }
  return offset + itemIdx
}

// ── 操作 ──

function doSearch(query: string) {
  const kw = (query || keyword.value).trim()
  if (!kw) return
  addToHistory(kw)
  trackSearch(kw)
  showDropdown.value = false
  activeIndex.value = -1
  keyword.value = ''
  sections.value = []
  emit('navigate', `/search?keyword=${encodeURIComponent(kw)}`)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    if (showDropdown.value && activeIndex.value >= 0 && activeIndex.value < flatItems.value.length) {
      // 选中下拉项
      const selectedItem = flatItems.value[activeIndex.value]
      if (selectedItem) doSearch(selectedItem.query)
    } else {
      doSearch(keyword.value)
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (!showDropdown.value) {
      showDropdown.value = true
      if (!keyword.value.trim()) fetchSuggestions('')
      activeIndex.value = 0
    } else {
      activeIndex.value = Math.min(activeIndex.value + 1, flatItems.value.length - 1)
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, -1)
  } else if (e.key === 'Escape') {
    showDropdown.value = false
    activeIndex.value = -1
  }
}

function handleFocus() {
  if (!keyword.value.trim()) {
    fetchSuggestions('')
  }
  showDropdown.value = true
}

// ── 点击外部关闭 ──
function onWindowClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const searchEl = document.querySelector('.header-search-wrapper')
  if (searchEl && !searchEl.contains(target)) {
    showDropdown.value = false
    activeIndex.value = -1
  }
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
})

onUnmounted(() => {
  window.removeEventListener('click', onWindowClick)
  if (debounceTimer) clearTimeout(debounceTimer)
})

// ── 快捷事件 ──
function handleGoCart() { emit('navigate', '/cart') }
function handleGoHome() { emit('navigate', '/') }
</script>

<template>
  <div class="bg-white border-b border-gray-100">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between py-5 gap-8">
        <!-- Logo -->
        <div class="flex-shrink-0 cursor-pointer" @click="handleGoHome">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            </div>
            <div>
              <h1 class="text-xl font-bold text-gray-900 tracking-tight">MALL</h1>
              <p class="text-[10px] text-gray-400 -mt-1 tracking-wider">正品好货</p>
            </div>
          </div>
        </div>

        <!-- 搜索区 -->
        <div class="flex-1 max-w-2xl header-search-wrapper">
          <div class="relative">
            <!-- 搜索输入框 + 按钮 -->
            <div class="flex">
              <div class="flex-1 relative">
                <input
                  v-model="keyword"
                  type="text"
                  placeholder="搜索商品、品牌..."
                  class="w-full h-10 pl-4 pr-4 text-sm border-2 border-red-600 rounded-l-md focus:outline-none focus:ring-0 bg-white text-gray-700 placeholder-gray-400"
                  @input="onInput"
                  @keydown="handleKeydown"
                  @focus="handleFocus"
                />
                <!-- loading 指示器 -->
                <div v-if="loading" class="absolute right-3 top-1/2 -translate-y-1/2">
                  <div class="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                </div>
              </div>
              <button
                class="h-10 px-8 bg-red-600 text-white text-sm font-medium rounded-r-md hover:bg-red-700 transition-colors flex items-center gap-2"
                @click="doSearch(keyword)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                搜索
              </button>
            </div>

            <!-- ====== 下拉建议面板 ====== -->
            <div
              v-if="showDropdown"
              class="absolute left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50 overflow-hidden"
            >
              <!-- 搜索历史 -->
              <div v-if="!keyword.trim() && loadHistory().length" class="px-4 py-3 border-b border-gray-100">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-gray-500 font-medium">搜索历史</span>
                  <button class="text-xs text-gray-400 hover:text-red-600" @click="clearHistory">清除</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="(q, idx) in loadHistory().slice(0, 8)"
                    :key="idx"
                    :class="[
                      'inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full transition-colors',
                      activeIndex === idx
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600',
                    ]"
                    @click.stop="doSearch(q)"
                  >
                    {{ q }}
                    <svg
                      v-if="activeIndex === idx"
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                      @click.stop="removeFromHistory(q)"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- API 返回的 section 区块 -->
              <div
                v-for="section in sections"
                :key="section.section_type"
                class="px-4 py-3"
                :class="{ 'border-b border-gray-100': section.section_type !== sections[sections.length - 1]?.section_type }"
              >
                <div class="flex items-center gap-2 mb-2">
                  <span
                    :class="[
                      'text-[10px] px-1.5 py-0.5 rounded font-medium',
                      section.section_type === 'autocomplete' ? 'bg-blue-100 text-blue-700' :
                      section.section_type === 'trending' ? 'bg-orange-100 text-orange-700' :
                      section.section_type === 'ai_suggestions' ? 'bg-purple-100 text-purple-700' :
                      'bg-gray-100 text-gray-700',
                    ]"
                  >
                    {{ section.section_type === 'autocomplete' ? '补全' :
                       section.section_type === 'trending' ? '热门' :
                       section.section_type === 'ai_suggestions' ? 'AI推荐' : section.title }}
                  </span>
                  <span class="text-xs text-gray-500">{{ section.section_type === 'ai_suggestions' ? '为你智能推荐' : '' }}</span>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="(item, idx) in section.queries"
                    :key="idx"
                    :class="[
                      'inline-flex items-center px-3 py-1 text-sm rounded-full transition-colors',
                      section.section_type === 'ai_suggestions'
                        ? 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200'
                        : section.section_type === 'trending'
                        ? 'bg-orange-50 text-orange-700 hover:bg-orange-100'
                        : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600',
                      activeIndex === getGlobalIndex(section, idx)
                        ? 'ring-2 ring-red-600 ring-offset-1'
                        : '',
                    ]"
                    @click.stop="doSearch(item.query)"
                  >
                    {{ item.query }}
                    <span
                      v-if="item.type === 'ai' && item.detail"
                      class="text-[10px] text-purple-400 ml-1"
                    >{{ item.detail }}</span>
                    <span
                      v-if="item.type === 'trending' && item.frequency"
                      class="text-[10px] text-orange-400 ml-1"
                    >{{ item.frequency }}</span>
                  </button>
                </div>
              </div>

              <!-- 无结果 -->
              <div
                v-if="!loadHistory().length && !sections.length && !loading"
                class="px-4 py-8 text-center text-sm text-gray-400"
              >
                输入关键词搜索商品
              </div>
            </div>
          </div>

          <!-- 热门搜索标签 (无输入时的默认展示) -->
          <div v-if="!showDropdown" class="flex items-center gap-3 mt-2">
            <span class="text-xs text-gray-400">热门搜索：</span>
            <button
              v-for="kw in ['手机', '笔记本电脑', '耳机', '运动鞋', '手表']"
              :key="kw"
              class="text-xs text-gray-500 hover:text-red-600 transition-colors"
              @click="doSearch(kw)"
            >
              {{ kw }}
            </button>
          </div>
        </div>

        <!-- 购物车入口 -->
        <div class="flex-shrink-0">
          <button
            class="flex items-center gap-2 h-10 px-5 border border-gray-200 rounded-md hover:border-red-600 hover:text-red-600 transition-colors text-sm text-gray-700 bg-white"
            @click="handleGoCart"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span>购物车</span>
            <span
              v-if="cartCount > 0"
              class="flex items-center justify-center min-w-5 h-5 px-1 bg-red-600 text-white text-xs font-medium rounded-full"
            >
              {{ cartCount > 99 ? '99+' : cartCount }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
