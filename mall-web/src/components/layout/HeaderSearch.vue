<script setup lang="ts">
/**
 * ============================================
 * 头部搜索区组件 (HeaderSearch)
 *
 * 两种模式:
 *   - overlay: 居中搜索浮层，Ctrl+K / Cmd+K 唤起，适合桌面三栏布局
 *   - inline:  内联搜索条 (原布局)，含 Logo + 搜索框 + 购物车入口
 *
 * 下拉面板 3 区:
 *   1. 搜索历史 (localStorage)
 *   2. 热门搜索 (API)
 *   3. AI 推荐 (API, prefix >= 2)
 *
 * 键盘导航: ↑↓ 移动高亮, Enter 选中, Esc 关闭
 * 自动补全: 150ms debounce
 * ============================================
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getSearchSuggestAPI, type SuggestSection, type SuggestQuery } from '@/apis/search'
import { trackSearch } from '@/utils/tracker'

const props = withDefaults(defineProps<{
  /** 显示模式: overlay (浮层) | inline (内联) */
  mode?: 'overlay' | 'inline'
}>(), {
  mode: 'overlay',
})

const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

const route = useRoute()

// ── 浮层开关 (overlay 模式) ──
const isOpen = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)

/** 打开搜索浮层 */
function open() {
  isOpen.value = true
  // 等 DOM 更新后聚焦输入框
  setTimeout(() => {
    const input = searchInput.value
    if (input) {
      input.focus()
      // 空输入时拉取热门/历史建议
      if (!keyword.value.trim()) fetchSuggestions('')
    }
  }, 120)
}

/** 关闭搜索浮层 */
function close() {
  isOpen.value = false
  sections.value = []
  activeIndex.value = -1
  showDropdown.value = false
}

// ── 快捷键 ──
function onKeydown(e: KeyboardEvent) {
  // Ctrl+K / Cmd+K：打开搜索浮层
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    open()
  }
  // Escape: 关闭
  if (e.key === 'Escape' && isOpen.value) {
    close()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const keyword = ref('')
const showDropdown = ref(false)
const activeIndex = ref(-1)
const loading = ref(false)

watch(
  () => route.query.keyword,
  (routeKeyword) => {
    keyword.value = typeof routeKeyword === 'string' ? routeKeyword : ''
  },
  { immediate: true },
)

// ── 搜索历史 (localStorage) ──
const HISTORY_KEY = '_snaptrip_search_history'
const MAX_HISTORY = 10

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item): item is string => typeof item === 'string')
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, MAX_HISTORY)
  } catch {
    return []
  }
}

const searchHistory = ref<string[]>(loadHistory())

function saveHistory(queries: string[]) {
  const normalized = [...new Set(queries.map((query) => query.trim()).filter(Boolean))]
    .slice(0, MAX_HISTORY)
  searchHistory.value = normalized
  try {
    if (normalized.length === 0) {
      localStorage.removeItem(HISTORY_KEY)
    } else {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(normalized))
    }
  } catch { /* quota exceeded — silently ignore */ }
}

function addToHistory(query: string) {
  saveHistory([query, ...searchHistory.value.filter((item) => item !== query)])
}

function removeFromHistory(query: string) {
  saveHistory(searchHistory.value.filter((item) => item !== query))
  activeIndex.value = -1
}

function clearHistory() {
  saveHistory([])
  activeIndex.value = -1
}

function syncHistory(event: StorageEvent) {
  if (event.key === HISTORY_KEY) {
    searchHistory.value = loadHistory()
  }
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
  if (!keyword.value.trim()) {
    for (const query of searchHistory.value) {
      items.push({ query, type: 'history', sectionIdx: -1 })
    }
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
  const historyLen = keyword.value.trim() ? 0 : searchHistory.value.length
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
  keyword.value = kw
  addToHistory(kw)
  trackSearch(kw)
  showDropdown.value = false
  activeIndex.value = -1
  sections.value = []
  if (isOpen.value) isOpen.value = false
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
  window.addEventListener('storage', syncHistory)
})

onUnmounted(() => {
  window.removeEventListener('click', onWindowClick)
  window.removeEventListener('storage', syncHistory)
  if (debounceTimer) clearTimeout(debounceTimer)
})

// ── 快捷事件 ──
function handleGoHome() { emit('navigate', '/') }
</script>

<template>
  <!-- =============================================================== -->
  <!-- Overlay 模式：居中搜索浮层 + 键盘快捷键唤起                       -->
  <!-- =============================================================== -->
  <Teleport to="body">
    <Transition name="search-overlay">
      <div
        v-if="mode === 'overlay' && isOpen"
        class="fixed inset-0 z-[100] flex items-start justify-center"
        :style="{ paddingTop: '18vh' }"
        @click.self="close"
      >
        <!-- 毛玻璃背景 -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />
        <!-- 搜索面板 (相对定位，置于毛玻璃之上) -->
        <div class="relative z-10 w-full max-w-[620px] mx-4">
          <div
            class="border-2 border-brand-600 rounded-[14px] overflow-hidden bg-white/95 shadow-2xl transition-shadow duration-300"
            :class="{ 'shadow-[0_0_0_4px_rgba(255,80,0,0.13)]': showDropdown }"
          >
            <!-- 搜索输入行 -->
            <div class="flex items-center h-[52px]">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 ml-5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
              </svg>
              <input
                ref="searchInput"
                v-model="keyword"
                type="text"
                placeholder="搜索商品、品牌..."
                class="flex-1 h-full pl-3 pr-3 text-[15px] border-none outline-none bg-transparent text-gray-700 placeholder-gray-400"
                @input="onInput"
                @keydown="handleKeydown"
                @focus="handleFocus"
              />
              <div v-if="loading" class="mr-3">
                <div class="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
              </div>
              <button
                class="h-[40px] px-8 mr-[3px] bg-brand-600 text-white text-sm font-medium rounded-[10px] hover:bg-brand-700 transition-colors flex-shrink-0"
                @click="doSearch(keyword)"
              >
                搜索
              </button>
              <!-- Esc 提示 -->
              <kbd class="hidden sm:inline-flex items-center gap-1 ml-2 mr-4 text-[12px] text-gray-400 bg-gray-100 rounded-md px-2 py-1 whitespace-nowrap flex-shrink-0 font-sans">
                Esc
              </kbd>
            </div>

            <!-- 下拉面板 — 线性展开 -->
            <div
              class="overflow-hidden transition-[max-height] duration-300 ease-linear"
              :style="{ maxHeight: showDropdown ? '600px' : '0px' }"
            >
              <div class="border-t border-gray-100">
              <!-- 搜索历史 -->
              <div v-if="!keyword.trim() && searchHistory.length" class="px-4 py-3 border-b border-gray-100">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-gray-500 font-medium">搜索历史</span>
                  <button class="text-xs text-gray-400 hover:text-brand-600" @pointerdown.prevent.stop="clearHistory">清除</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <div
                    v-for="(q, idx) in searchHistory.slice(0, 8)"
                    :key="q"
                    :class="[
                      'inline-flex items-center overflow-hidden text-sm rounded-full transition-colors',
                      activeIndex === idx
                        ? 'bg-brand-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-brand-50 hover:text-brand-600',
                    ]"
                  >
                    <button class="py-1 pl-3 pr-1" @pointerdown.prevent.stop="doSearch(q)">{{ q }}</button>
                    <button
                      class="py-1 pl-1 pr-2 opacity-60 hover:opacity-100"
                      :aria-label="`删除搜索历史：${q}`"
                      @pointerdown.prevent.stop="removeFromHistory(q)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
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
                        : 'bg-gray-100 text-gray-600 hover:bg-brand-50 hover:text-brand-600',
                      activeIndex === getGlobalIndex(section, idx)
                        ? 'ring-2 ring-brand-600 ring-offset-1'
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
                v-if="!searchHistory.length && !sections.length && !loading"
                class="px-4 py-8 text-center text-sm text-gray-400"
              >
                输入关键词搜索商品
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- =============================================================== -->
  <!-- Inline 模式：页面顶部搜索条，随页面自然滚动                         -->
  <!-- =============================================================== -->
  <div v-if="mode === 'inline'" class="inline-search-fixed">
    <div class="header-search-wrapper" :class="{ 'is-expanded': showDropdown }">
      <div class="taobao-search-shell">
        <div class="taobao-search-main">
          <svg class="search-leading-icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
            <path d="m15.5 15.5 4 4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="2" />
          </svg>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索宝贝、品牌、好物"
            class="taobao-search-input"
            @input="onInput"
            @keydown="handleKeydown"
            @focus="handleFocus"
          />
          <button
            v-if="keyword"
            type="button"
            class="search-clear"
            aria-label="清空搜索内容"
            @click="keyword = ''; onInput()"
          >
            ×
          </button>
          <div v-if="loading" class="search-loading" aria-label="正在加载搜索建议">
            <span />
          </div>
          <button type="button" class="taobao-search-button" @click="doSearch(keyword)">
            搜索
          </button>
        </div>

        <div class="search-suggestion-panel" :class="{ open: showDropdown }">
          <div class="suggestion-content">
              <!-- 搜索历史 -->
              <div v-if="!keyword.trim() && searchHistory.length" class="px-4 py-3 border-b border-gray-100">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-gray-500 font-medium">搜索历史</span>
                  <button class="text-xs text-gray-400 hover:text-brand-600" @pointerdown.prevent.stop="clearHistory">清除</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <div
                    v-for="(q, idx) in searchHistory.slice(0, 8)"
                    :key="q"
                    :class="[
                      'inline-flex items-center overflow-hidden text-sm rounded-full transition-colors',
                      activeIndex === idx
                        ? 'bg-brand-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-brand-50 hover:text-brand-600',
                    ]"
                  >
                    <button class="py-1 pl-3 pr-1" @pointerdown.prevent.stop="doSearch(q)">{{ q }}</button>
                    <button
                      class="py-1 pl-1 pr-2 opacity-60 hover:opacity-100"
                      :aria-label="`删除搜索历史：${q}`"
                      @pointerdown.prevent.stop="removeFromHistory(q)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
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
                        : 'bg-gray-100 text-gray-600 hover:bg-brand-50 hover:text-brand-600',
                      activeIndex === getGlobalIndex(section, idx)
                        ? 'ring-2 ring-brand-600 ring-offset-1'
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
                v-if="!searchHistory.length && !sections.length && !loading"
                class="px-4 py-8 text-center text-sm text-gray-400"
              >
                输入关键词搜索商品
              </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ================================================================
   Overlay 过渡
   ================================================================ */
.search-overlay-enter-active,
.search-overlay-leave-active {
  transition: opacity 0.2s ease;
}
.search-overlay-enter-from,
.search-overlay-leave-to {
  opacity: 0;
}

/* ================================================================
   Inline 模式：页面顶部搜索条
   ================================================================ */
.inline-search-fixed {
  position: relative;
  z-index: 50;
  padding: 52px 19px 12px 208px;
}

.header-search-wrapper {
  width: min(720px, calc(100% - 32px));
  margin: 0 auto;
  border-radius: 24px;
  transition: filter 0.2s ease;
}

.header-search-wrapper.is-expanded {
  filter: drop-shadow(0 14px 24px rgba(255, 80, 0, 0.12));
}

.taobao-search-shell {
  overflow: hidden;
  border: 2px solid #ff5000;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 4px 14px rgba(255, 80, 0, 0.08);
  transition: box-shadow 0.2s ease;
}

.header-search-wrapper.is-expanded .taobao-search-shell {
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
}

.taobao-search-main {
  display: flex;
  height: 46px;
  align-items: center;
  padding-left: 4px;
}

.search-leading-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  margin-left: 14px;
  color: #999;
}

.taobao-search-input {
  min-width: 0;
  height: 100%;
  flex: 1;
  padding: 0 10px;
  border: 0;
  outline: 0;
  color: #222;
  background: transparent;
  font-size: 14px;
}

.taobao-search-input::placeholder {
  color: #aaa;
}

.taobao-search-input::-webkit-search-cancel-button {
  display: none;
}

.search-clear {
  display: flex;
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #aaa;
  font-size: 19px;
  line-height: 1;
}

.search-clear:hover {
  color: #666;
  background: #f5f5f5;
}

.search-loading {
  width: 28px;
  flex: 0 0 auto;
}

.search-loading span {
  display: block;
  width: 15px;
  height: 15px;
  margin: auto;
  border: 2px solid #ffb28f;
  border-top-color: #ff5000;
  border-radius: 50%;
  animation: search-spin 0.75s linear infinite;
}

.taobao-search-button {
  height: 38px;
  min-width: 82px;
  flex: 0 0 auto;
  margin-right: 3px;
  border-radius: 19px;
  color: #fff;
  background: linear-gradient(90deg, #ff8a00 0%, #ff5000 62%, #ff3d00 100%);
  box-shadow: 0 3px 8px rgba(255, 80, 0, 0.22);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  transition: filter 0.2s ease, transform 0.2s ease;
}

.taobao-search-button:hover {
  filter: brightness(1.04);
}

.taobao-search-button:active {
  transform: scale(0.98);
}

.search-suggestion-panel {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.25s ease, opacity 0.18s ease;
}

.search-suggestion-panel.open {
  max-height: 560px;
  opacity: 1;
}

.suggestion-content {
  max-height: 500px;
  overflow-y: auto;
  border-top: 1px solid #f1f1f1;
  background: #fff;
}

@keyframes search-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1023px) {
  .inline-search-fixed {
    padding-left: 19px;
  }
}

@media (max-width: 640px) {
  .inline-search-fixed {
    padding-right: 8px;
    padding-left: 8px;
  }

  .header-search-wrapper {
    width: 100%;
  }

  .search-leading-icon {
    margin-left: 14px;
  }

  .taobao-search-button {
    min-width: 68px;
  }
}
</style>
