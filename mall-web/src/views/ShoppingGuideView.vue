<script setup lang="ts">
/**
 * ============================================
 * 帮我挑 — AI 购物助手页面
 *
 * 默认：新对话页面，居中输入框 + 预测 query
 * FAQ：全宽对话，无 Canvas
 * 商品搜索/信息搜索：左对话 + 右 Canvas，Canvas 动画滑入
 * ============================================
 */
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useShoppingGuideStore } from '@/stores/shoppingGuide'
import type { SearchMode } from '@/stores/shoppingGuide'
import type { RecommendedProduct, ShoppingContext } from '@/apis/shoppingGuide'
import type { PmsProduct } from '@/types/product'
import { renderMarkdown } from '@/composables/useMarkdown'
import { getSearchSuggestAPI } from '@/apis/search'
import type { FollowUpItem } from '@/apis/shoppingGuide'
import ProductCard from '@/components/product/ProductCard.vue'
import InfoCardsPanel from '@/components/product/InfoCardsPanel.vue'
import FollowUpPrompt from '@/components/shopping-guide/FollowUpPrompt.vue'

const route = useRoute()
const router = useRouter()
const store = useShoppingGuideStore()

const MODE_LIST: { value: SearchMode; label: string; desc: string }[] = [
  { value: 'auto', label: '自动', desc: 'AI 自动判断信息或商品搜索' },
  { value: 'info', label: '信息搜索', desc: '获取选购建议、攻略、对比信息' },
  { value: 'product', label: '商品搜索', desc: '直接搜索并展示商品列表' },
]

function buildContext(): ShoppingContext | null {
  const ctx: ShoppingContext = {}
  if (route.params.id && String(route.path).startsWith('/product/')) {
    ctx.current_product_id = route.params.id as string
  }
  if (String(route.path).startsWith('/category')) {
    ctx.current_category = (route.query.cat as string) || null
  }
  if (route.path === '/search' && route.query.keyword) {
    ctx.search_query = route.query.keyword as string
  }
  return Object.values(ctx).some(v => v) ? ctx : null
}

const input = ref('')
const msgContainer = ref<HTMLElement | null>(null)

// ═══════════════════════════════════════════
// Canvas 分屏
// ═══════════════════════════════════════════
const splitPercent = ref(36)
const isDragging = ref(false)
const splitContainer = ref<HTMLElement | null>(null)
const MIN_LEFT_PCT = 24
const MAX_LEFT_PCT = 55

const latestAssistantMessage = computed(() => {
  for (let i = store.messages.length - 1; i >= 0; i--) {
    if (store.messages[i]?.role === 'assistant') return store.messages[i]
  }
  return null
})
const latestInfoCards = computed(() => latestAssistantMessage.value?.infoCards ?? null)
const latestFollowUps = computed<FollowUpItem[]>(() =>
  latestAssistantMessage.value?.followUps ?? [],
)

/** 是否显示 Canvas：用户选择 info/product 模式时始终展开；auto 模式下有结构化数据才展开 */
const showCanvas = computed(() => {
  // 显式选择了 info/product 模式 → 始终展开（即使 streamMode 尚未返回）
  if (store.searchMode === 'info' || store.searchMode === 'product') return true
  // streamMode 收到后立即展开（后端 intent 分类结果）
  if (store.streamMode === 'info' || store.streamMode === 'product') return true
  if (!latestAssistantMessage.value) return false
  // auto 模式：有商品卡片或信息卡片时才显示
  const last = latestAssistantMessage.value
  return !!(last.products?.length || last.infoCards)
})

/** Canvas 已展开但内容未到达——展示骨架屏 */
const canvasLoading = computed(() =>
  showCanvas.value && store.loading && !latestInfoCards.value && !canvasProducts.value.length,
)

/** Canvas 是否可见（带动画过渡） */
const canvasVisible = ref(false)
watch(showCanvas, (val) => {
  if (val) canvasVisible.value = true
  else {
    // 延迟隐藏以等待动画结束
    setTimeout(() => { canvasVisible.value = false }, 300)
  }
}, { immediate: true })

const hasCanvasContent = computed(() => showCanvas.value && canvasVisible.value)

/** 是否新对话 */
const isNewConversation = computed(() => !store.hasMessages)

function onDividerMouseDown(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}
function onMouseMove(e: MouseEvent) {
  if (!isDragging.value || !splitContainer.value) return
  const rect = splitContainer.value.getBoundingClientRect()
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  splitPercent.value = Math.min(MAX_LEFT_PCT, Math.max(MIN_LEFT_PCT, pct))
}
function onMouseUp() {
  if (!isDragging.value) return
  isDragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('click', closeModeMenu)
  store.loadSessions()
  store.newSession()
  fetchPredictedQueries()
})
onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('click', closeModeMenu)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
})

// ═══════════════════════════════════════════
// 历史对话下拉
// ═══════════════════════════════════════════
const historyOpen = ref(false)
const historyWrapRef = ref<HTMLElement | null>(null)
function closeHistoryDropdown(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (historyWrapRef.value && !historyWrapRef.value.contains(target)) historyOpen.value = false
}
onMounted(() => window.addEventListener('click', closeHistoryDropdown))
onUnmounted(() => window.removeEventListener('click', closeHistoryDropdown))

function handleNewSession() { store.newSession(); historyOpen.value = false }
function handleLoadSession(id: string) { store.loadSession(id); historyOpen.value = false }

function formatTime(iso: string | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ═══════════════════════════════════════════
// 模式切换
// ═══════════════════════════════════════════
const modeMenuOpen = ref(false)
const modeMenuRef = ref<HTMLElement | null>(null)
function setMode(mode: SearchMode) { store.setSearchMode(mode); modeMenuOpen.value = false }
function toggleModeMenu() { modeMenuOpen.value = !modeMenuOpen.value }
function closeModeMenu(e: MouseEvent) {
  if (modeMenuRef.value && !modeMenuRef.value.contains(e.target as HTMLElement)) modeMenuOpen.value = false
}
const currentModeLabel = computed(() => MODE_LIST.find(m => m.value === store.searchMode)?.label || '自动')

// ═══════════════════════════════════════════
// 滚动 — 仅当用户在底部附近（100px）时自动滚动
// ═══════════════════════════════════════════
function isNearBottom(): boolean {
  if (!msgContainer.value) return true
  const { scrollTop, scrollHeight, clientHeight } = msgContainer.value
  return scrollHeight - scrollTop - clientHeight < 100
}
async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
}
async function scrollToBottomIfAtBottom() {
  await nextTick()
  if (msgContainer.value && isNearBottom()) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}
// 新消息到来始终滚到底（用户主动发消息）；流式内容仅当在底部时才滚
watch(() => store.messages.length, scrollToBottom)
watch(() => store.loading, scrollToBottomIfAtBottom)
watch(() => {
  const msgs = store.messages
  if (!msgs.length) return ''
  const last = msgs[msgs.length - 1]
  return last?.role === 'assistant' && store.loading ? last.content : ''
}, scrollToBottomIfAtBottom)

/** 正在流式输出的消息索引 — 用于显示闪烁光标 */
const streamingMsgIndex = computed(() => {
  if (!store.loading) return -1
  const msgs = store.messages
  if (!msgs.length) return -1
  const last = msgs[msgs.length - 1]
  if (last.role === 'assistant' && last.content) return msgs.length - 1
  return -1
})

// ═══════════════════════════════════════════
// 消息操作
// ═══════════════════════════════════════════
async function handleSend() {
  if (!input.value.trim() || store.loading) return
  const text = input.value.trim()
  await store.sendMessage(text, buildContext())
  input.value = ''
}
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
}
function handleFollowUpSend(text: string) { store.sendFollowUp(text, buildContext()) }
async function handleFollowUpFill(text: string) {
  input.value = text
  await nextTick()
  const ta = document.querySelector('.sg-footer .sg-input') as HTMLTextAreaElement | null
  ta?.focus()
}

// ═══════════════════════════════════════════
// 预测问题 — 基于历史 + 热门搜索
// ═══════════════════════════════════════════
const FALLBACK_QUERIES = [
  '小米17怎么样',
  '200 元以内的蓝牙耳机',
  '学生党性价比高的笔记本',
  '华为P20值不值得买',
  '索尼降噪耳机推荐',
  '送给女朋友的生日礼物',
  'MacBook Pro 评测',
  '快过年了有什么年货推荐',
]

const predictedQueries = ref<string[]>([])
const loadedPredictedQueries = ref(false)

async function fetchPredictedQueries() {
  if (loadedPredictedQueries.value) return
  try {
    const res = await getSearchSuggestAPI({ prefix: '', limit: 8 })
    const seen = new Set<string>()
    const queries: string[] = []
    for (const section of res.sections || []) {
      if (section.section_type === 'history' || section.section_type === 'trending') {
        for (const q of section.queries || []) {
          if (q.query && !seen.has(q.query)) {
            seen.add(q.query)
            queries.push(q.query)
          }
        }
      }
    }
    if (queries.length > 0) {
      predictedQueries.value = queries.slice(0, 8)
      loadedPredictedQueries.value = true
    }
  } catch {
    // use fallback
  }
}

const displayQueries = computed(() =>
  predictedQueries.value.length > 0 ? predictedQueries.value : FALLBACK_QUERIES,
)

// 输入框内滚动预测
const currentPredictionIndex = ref(0)
const predictionKey = ref(0)
let _rotateTimer: ReturnType<typeof setInterval> | null = null

const rotatingPlaceholder = computed(() => {
  const list = displayQueries.value
  if (!list.length) return '输入你的需求...'
  return list[currentPredictionIndex.value] || list[0]
})

function startPredictionRotation() {
  stopPredictionRotation()
  _rotateTimer = setInterval(() => {
    const list = displayQueries.value
    if (!list.length) return
    currentPredictionIndex.value = (currentPredictionIndex.value + 1) % list.length
    predictionKey.value++
  }, 3000)
}

function stopPredictionRotation() {
  if (_rotateTimer) { clearInterval(_rotateTimer); _rotateTimer = null }
}

function usePrediction(q: string) {
  input.value = q
}

function fillInputFromPlaceholder() {
  if (!input.value && rotatingPlaceholder.value) {
    input.value = rotatingPlaceholder.value
  }
}

watch(displayQueries, (list) => {
  if (list.length > 0) {
    currentPredictionIndex.value = 0
    predictionKey.value++
    startPredictionRotation()
  }
}, { immediate: true })

onUnmounted(() => { stopPredictionRotation() })

// ═══════════════════════════════════════════
// 商品映射
// ═══════════════════════════════════════════
const canvasProducts = computed<PmsProduct[]>(() =>
  store.recommendedProducts.map(mapToPmsProduct),
)
function mapToPmsProduct(p: RecommendedProduct): PmsProduct {
  const productId = p.productId || (p.link ? p.link.split('/').pop() || '' : '')
  return {
    id: productId, name: p.name, price: p.price, originalPrice: p.originalPrice || undefined,
    defaultPic: p.imageUrl || null, brandName: p.brandName || null,
    saleCount: p.saleCount || undefined, subTitle: null, promotionPrice: undefined,
    promotionType: undefined, stock: 0, categoryId: null, newStatus: undefined,
    recommendStatus: undefined,
  }
}

function goProductDetail(id: string) {
  if (!id || id === 'undefined') return
  router.push(`/product/${id}`)
}
</script>

<template>
  <div
    ref="splitContainer"
    class="sg-canvas-page"
    :class="{
      'sg-canvas-page--dragging': isDragging,
      'sg-canvas-page--new': isNewConversation,
      'sg-canvas-page--split': hasCanvasContent,
    }"
  >
    <!-- ═══ 左侧：对话面板 ═══ -->
    <div
      class="sg-chat-panel"
      :style="hasCanvasContent ? { width: splitPercent + '%' } : {}"
    >
      <!-- 顶栏（有对话时才显示） -->
      <div v-if="!isNewConversation" class="sg-left-topbar">
        <div class="sg-left-actions">
          <div ref="historyWrapRef" class="sg-history-wrap">
            <button class="sg-action-btn" :class="{ active: historyOpen }" @click.stop="historyOpen = !historyOpen">
              <svg xmlns="http://www.w3.org/2000/svg" class="sg-action-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span>历史</span>
            </button>
            <div v-if="historyOpen" class="sg-history-dropdown">
              <div class="sg-history-dropdown-header">
                <span>历史对话</span>
                <button class="sg-text-btn" @click="store.loadSessions()">刷新</button>
              </div>
              <div v-if="store.sessionsLoading" class="sg-history-empty">加载中...</div>
              <div v-else-if="!store.sessions.length" class="sg-history-empty">暂无历史对话</div>
              <div v-else class="sg-history-list">
                <button v-for="s in store.sessions" :key="s.id" class="sg-history-item"
                  :class="{ active: store.sessionId === s.id }" @click="handleLoadSession(s.id)">
                  <span class="sg-history-title">{{ s.summary || '新对话' }}</span>
                  <span class="sg-history-time">{{ formatTime(s.updatedAt) }}</span>
                </button>
              </div>
            </div>
          </div>
          <button class="sg-action-btn" @click="handleNewSession">
            <svg xmlns="http://www.w3.org/2000/svg" class="sg-action-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <span>新对话</span>
          </button>
        </div>
      </div>

      <!-- ═══ 新对话：居中 Hero ═══ -->
      <template v-if="isNewConversation">
        <div class="sg-hero-center">
          <div class="sg-hero-center-inner">
            <h1 class="sg-hero-title">帮我挑</h1>
            <p class="sg-hero-subtitle">AI 购物助手，帮你挑选、比价、决策</p>

            <!-- 居中输入框 -->
            <div class="sg-hero-input-area">
              <div class="sg-input-wrap sg-input-wrap--hero" @click="fillInputFromPlaceholder">
                <div class="sg-input-placeholder-wrap">
                  <textarea
                    v-model="input"
                    class="sg-input"
                    placeholder=""
                    rows="1"
                    :disabled="store.loading"
                    @keydown="handleKeydown"
                    @input="(e) => {
                      const t = (e.target as HTMLTextAreaElement)
                      t.style.height = 'auto'
                      t.style.height = Math.min(t.scrollHeight, 120) + 'px'
                    }"
                  />
                  <div v-if="!input" class="sg-rotating-ph">
                    <Transition name="ph-roll" mode="out-in">
                      <span :key="predictionKey" class="sg-rotating-ph-text">
                        {{ rotatingPlaceholder }}
                      </span>
                    </Transition>
                  </div>
                </div>
                <button class="sg-send-btn" :disabled="!input.trim() || store.loading" @click="handleSend">
                  <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="sg-send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                  </svg>
                  <div v-else class="sg-spinner" />
                </button>
              </div>
            </div>

            <!-- 底部模式选择 -->
            <div ref="modeMenuRef" class="sg-mode-picker sg-mode-picker--hero">
              <button class="sg-mode-current" @click="toggleModeMenu">
                <span>{{ currentModeLabel }}</span>
                <svg xmlns="http://www.w3.org/2000/svg" class="sg-mode-chevron" :class="{ open: modeMenuOpen }"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
                </svg>
              </button>
              <div v-if="modeMenuOpen" class="sg-mode-popup">
                <button v-for="m in MODE_LIST" :key="m.value" class="sg-mode-option"
                  :class="{ active: store.searchMode === m.value }" @click="setMode(m.value)">
                  <span class="sg-mode-option-label">{{ m.label }}</span>
                  <span class="sg-mode-option-desc">{{ m.desc }}</span>
                </button>
              </div>
            </div>

            <div class="sg-footer-hint">内容由 AI 生成，仅供参考</div>
          </div>
        </div>
      </template>

      <!-- ═══ 有对话：聊天区 ═══ -->
      <template v-else>
        <div ref="msgContainer" class="sg-chat">
          <div class="sg-chat-inner">
            <div v-for="(msg, i) in store.messages" :key="i" class="sg-msg" :class="{ 'sg-msg--user': msg.role === 'user' }">
              <div class="sg-bubble-col">
                <div class="sg-bubble" :class="{ 'sg-bubble--user': msg.role === 'user', 'sg-bubble--streaming': i === streamingMsgIndex }">
                  <div class="sg-bubble-text" v-html="renderMarkdown(msg.content)" />
                </div>
              </div>
            </div>

            <!-- 加载动画：仅在等待首个 token 时显示 -->
            <div v-if="store.loading && store.messages.length && store.messages[store.messages.length - 1]?.role === 'assistant' && !store.messages[store.messages.length - 1]?.content" class="sg-typing">
              <span class="sg-typing-dot" /><span class="sg-typing-dot" /><span class="sg-typing-dot" />
            </div>
          </div>
        </div>

        <!-- 猜你想问 -->
        <div v-if="latestFollowUps.length && !store.loading" class="sg-followup-prompt-wrap">
          <FollowUpPrompt
            :items="latestFollowUps"
            :disabled="store.loading"
            @select="handleFollowUpSend"
            @fill="handleFollowUpFill"
          />
        </div>

        <!-- 输入区 -->
        <footer class="sg-footer">
          <div class="sg-footer-inner">
            <div class="sg-input-wrap">
              <textarea v-model="input" class="sg-input"
                :placeholder="store.searchMode === 'product' ? '输入想搜索的商品关键词...'
                  : store.searchMode === 'info' ? '输入想了解的信息，如选购攻略、对比...'
                  : '输入你的需求...'"
                rows="1" :disabled="store.loading"
                @keydown="handleKeydown"
                @input="(e) => { const t = (e.target as HTMLTextAreaElement); t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 120) + 'px' }"
              />
              <button class="sg-send-btn" :disabled="!input.trim() || store.loading" @click="handleSend">
                <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="sg-send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
                <div v-else class="sg-spinner" />
              </button>
            </div>

            <div ref="modeMenuRef" class="sg-mode-picker">
              <button class="sg-mode-current" @click="toggleModeMenu">
                <span>{{ currentModeLabel }}</span>
                <svg xmlns="http://www.w3.org/2000/svg" class="sg-mode-chevron" :class="{ open: modeMenuOpen }"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
                </svg>
              </button>
              <div v-if="modeMenuOpen" class="sg-mode-popup">
                <button v-for="m in MODE_LIST" :key="m.value" class="sg-mode-option"
                  :class="{ active: store.searchMode === m.value }" @click="setMode(m.value)">
                  <span class="sg-mode-option-label">{{ m.label }}</span>
                  <span class="sg-mode-option-desc">{{ m.desc }}</span>
                </button>
              </div>
            </div>

            <div class="sg-footer-hint">内容由 AI 生成，仅供参考</div>
          </div>
        </footer>
      </template>
    </div>

    <!-- ═══ 分隔线（仅 Canvas 可见时） ═══ -->
    <div v-if="hasCanvasContent" class="sg-divider" @mousedown="onDividerMouseDown">
      <div class="sg-divider-handle" />
    </div>

    <!-- ═══ 右侧：内容画布（仅 Canvas 可见时） ═══ -->
    <div
      v-if="canvasVisible"
      class="sg-canvas-panel"
      :class="{ 'sg-canvas-panel--enter': showCanvas }"
      :style="{ width: (100 - splitPercent) + '%' }"
    >
      <!-- 商品搜索结果 -->
      <template v-if="canvasProducts.length">
        <div class="sg-right-section">
          <div class="sg-canvas-header">
            <span class="sg-canvas-title">AI 推荐商品</span>
            <span class="sg-canvas-count">{{ canvasProducts.length }} 件</span>
          </div>
          <div class="sg-canvas-grid">
            <ProductCard v-for="p in canvasProducts" :key="p.id || p.name"
              :product="p" @click="goProductDetail(p.id)" />
          </div>
        </div>
      </template>

      <!-- Canvas 加载骨架 -->
      <div v-if="canvasLoading" class="sg-canvas-skeleton">
        <div class="sg-skel-line sg-skel-line--title" />
        <div class="sg-skel-line" />
        <div class="sg-skel-line sg-skel-line--short" />
        <div class="sg-skel-line" />
        <div class="sg-skel-line sg-skel-line--short" />
      </div>

      <!-- 信息搜索卡片 -->
      <InfoCardsPanel v-else-if="latestInfoCards" :cards="latestInfoCards" />

      <!-- 兜底：有 AI 回复但无结构化卡片时，渲染 Markdown -->
      <div v-else-if="latestAssistantMessage" class="sg-canvas-markdown-fallback">
        <div class="sg-canvas-markdown-body" v-html="renderMarkdown(latestAssistantMessage.content)" />
      </div>

      <!-- 无内容 -->
      <div v-else class="sg-canvas-empty-state">
        <p style="color:#999;font-size:13px;text-align:center;padding:20px">
          输入需求，AI 将为你自动推荐
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   Canvas 页面容器
   ═══════════════════════════════════════════ */
.sg-canvas-page {
  display: flex;
  width: 100%;
  height: calc(100vh - 106px - 24px);
  min-height: 500px;
  border-radius: 12px;
  overflow: hidden;
  background: transparent;
  transition: all 0.3s ease;
}
.sg-canvas-page--dragging { cursor: col-resize; }

/* ═══════════════════════════════════════════
   左侧：对话面板
   ═══════════════════════════════════════════ */
.sg-chat-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 280px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  overflow: hidden;
  transition: width 0.3s ease;
}

/* ── 顶栏 ── */
.sg-left-topbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06); flex-shrink: 0;
}
.sg-left-actions { display: flex; align-items: center; gap: 6px; }
.sg-history-wrap { position: relative; }
.sg-action-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 10px; border-radius: 8px;
  font-size: 12px; font-weight: 500; color: #666;
  background: rgba(0, 0, 0, 0.03); transition: all 0.15s;
}
.sg-action-btn:hover { background: rgba(0, 0, 0, 0.07); color: #333; }
.sg-action-btn.active { background: rgba(255, 80, 0, 0.1); color: #ff5000; }
.sg-action-icon { width: 14px; height: 14px; }

/* ── 历史下拉 ── */
.sg-history-dropdown {
  position: absolute; top: calc(100% + 6px); left: 0; width: 260px; max-height: 360px;
  background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12); z-index: 30;
  overflow: hidden; display: flex; flex-direction: column;
}
.sg-history-dropdown-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 13px; font-weight: 600; color: #333;
}
.sg-text-btn { font-size: 11px; color: #999; transition: color 0.15s; }
.sg-text-btn:hover { color: #ff5000; }
.sg-history-list { overflow-y: auto; padding: 4px; }
.sg-history-empty { padding: 20px 12px; text-align: center; font-size: 12px; color: #bbb; }
.sg-history-item {
  display: flex; flex-direction: column; gap: 2px; width: 100%; text-align: left;
  padding: 8px 10px; border-radius: 8px; transition: background 0.15s;
}
.sg-history-item:hover { background: rgba(0, 0, 0, 0.04); }
.sg-history-item.active { background: rgba(255, 80, 0, 0.08); }
.sg-history-title { font-size: 12px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sg-history-time { font-size: 11px; color: #999; }

/* ═══════════════════════════════════════════
   新对话 — 居中 Hero
   ═══════════════════════════════════════════ */
.sg-hero-center {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 40px 24px;
}
.sg-hero-center-inner {
  display: flex; flex-direction: column; align-items: center;
  max-width: 600px; width: 100%; gap: 20px;
}
.sg-hero-title {
  font-size: 32px; font-weight: 700; color: #1a1a1a;
  background: linear-gradient(135deg, #ff5000, #f97316);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}
.sg-hero-subtitle { font-size: 15px; color: #999; margin: 0; }

.sg-hero-input-area {
  width: 100%; display: flex; flex-direction: column; gap: 12px;
}

/* ── 输入框内旋转占位 ── */
.sg-input-placeholder-wrap {
  position: relative; flex: 1; display: flex; align-items: center; min-height: 24px;
}
.sg-rotating-ph {
  position: absolute; inset: 0; pointer-events: none;
  display: flex; align-items: center; overflow: hidden;
}
.sg-rotating-ph-text {
  font-size: 13px; color: #bbb; white-space: nowrap; line-height: 1.5;
}

/* 滚动动画：新元素从下方滑入，旧元素向上滑出 */
.ph-roll-enter-active {
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.ph-roll-leave-active {
  transition: all 0.25s cubic-bezier(0.55, 0.055, 0.675, 0.19);
  position: absolute;
}
.ph-roll-enter-from {
  opacity: 0; transform: translateY(18px);
}
.ph-roll-leave-to {
  opacity: 0; transform: translateY(-18px);
}

/* ── 模式选择器（居中时） ── */
.sg-mode-picker--hero { margin-top: 4px; }

/* ── 模式选择器 ── */
.sg-mode-picker { position: relative; align-self: flex-start; margin-top: 6px; }
.sg-mode-current {
  display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
  font-size: 11px; font-weight: 500; color: #999;
  background: rgba(0, 0, 0, 0.03); border-radius: 6px; transition: all 0.15s;
}
.sg-mode-current:hover { color: #666; background: rgba(0, 0, 0, 0.06); }
.sg-mode-chevron { width: 12px; height: 12px; transition: transform 0.2s; }
.sg-mode-chevron.open { transform: rotate(180deg); }

.sg-mode-popup {
  position: absolute; bottom: calc(100% + 6px); left: 0; width: 220px;
  background: rgba(255, 255, 255, 0.97); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); overflow: hidden; z-index: 20;
}
.sg-mode-option {
  display: flex; flex-direction: column; gap: 1px; width: 100%; text-align: left;
  padding: 10px 14px; transition: background 0.15s;
}
.sg-mode-option:hover { background: rgba(0, 0, 0, 0.04); }
.sg-mode-option.active { background: rgba(255, 80, 0, 0.06); }
.sg-mode-option + .sg-mode-option { border-top: 1px solid rgba(0, 0, 0, 0.04); }
.sg-mode-option-label { font-size: 13px; font-weight: 600; color: #333; }
.sg-mode-option.active .sg-mode-option-label { color: #ff5000; }
.sg-mode-option-desc { font-size: 11px; color: #aaa; margin-top: 1px; }

/* ── 对话区 ── */
.sg-chat { flex: 1; overflow-y: auto; padding: 16px 0; }
.sg-chat-inner {
  max-width: 640px; margin: 0 auto; padding: 0 20px;
  display: flex; flex-direction: column; gap: 16px;
}

/* ── 消息 ── */
.sg-msg { display: flex; gap: 10px; }
.sg-msg--user { flex-direction: row-reverse; }
.sg-bubble-col { max-width: 100%; display: flex; flex-direction: column; gap: 8px; }
.sg-bubble {
  padding: 10px 16px; border-radius: 14px; background: #fff;
  font-size: 13px; line-height: 1.65; color: #333;
}
.sg-bubble--user { background: #ff5000; color: #fff; }

/* ── 输入区 ── */
.sg-footer { border-top: 1px solid rgba(0, 0, 0, 0.06); flex-shrink: 0; padding: 10px 16px 12px; }
.sg-footer-inner { max-width: 100%; }
.sg-footer-hint { margin-top: 6px; font-size: 11px; color: #bbb; text-align: center; }

.sg-input-wrap {
  display: flex; align-items: flex-end; gap: 8px;
  padding: 7px 7px 7px 16px; background: rgba(0, 0, 0, 0.04);
  border-radius: 14px; border: 2px solid transparent; transition: all 0.2s;
}
.sg-input-wrap--hero {
  background: rgba(0, 0, 0, 0.02); border-radius: 16px; padding: 10px 10px 10px 20px;
}
.sg-input-wrap:focus-within { border-color: #ff5000; background: #fff; }
.sg-input {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 13px; line-height: 1.5; color: #333;
  resize: none; max-height: 100px; padding: 3px 0;
}
.sg-input::placeholder { color: #bbb; }

.sg-send-btn {
  width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
  border-radius: 10px; background: #ff5000; color: #fff; flex-shrink: 0; transition: all 0.15s;
}
.sg-send-btn:hover:not(:disabled) { background: #e64800; }
.sg-send-btn:disabled { background: #e0e0e0; color: #bbb; }
.sg-send-icon { width: 16px; height: 16px; }

.sg-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 流式输出闪烁光标 ── */
.sg-bubble--streaming .sg-bubble-text :deep(> *:last-child::after) {
  content: '_';
  animation: cursor-blink 1s steps(5, start) infinite;
  font-weight: 700;
  margin-left: 2px;
}
.sg-bubble--streaming .sg-bubble-text :deep(> ol:last-child li:last-child::after),
.sg-bubble--streaming .sg-bubble-text :deep(> ul:last-child li:last-child::after),
.sg-bubble--streaming .sg-bubble-text :deep(> pre:last-child code::after) {
  content: '_';
  animation: cursor-blink 1s steps(5, start) infinite;
  font-weight: 700;
  margin-left: 2px;
}
@keyframes cursor-blink {
  to { visibility: hidden; }
}

/* ── Markdown ── */
.sg-bubble-text :deep(p) { margin: 0 0 6px; }
.sg-bubble-text :deep(p:last-child) { margin-bottom: 0; }
.sg-bubble-text :deep(ul), .sg-bubble-text :deep(ol) { margin: 4px 0 6px; padding-left: 18px; }
.sg-bubble-text :deep(li) { margin-bottom: 2px; }
.sg-bubble-text :deep(a) { color: #ff5000; text-decoration: underline; }
.sg-bubble-text :deep(code) { background: rgba(0, 0, 0, 0.06); padding: 2px 5px; border-radius: 4px; font-size: 12px; }
.sg-bubble-text :deep(pre) { background: #f5f5f5; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; margin: 8px 0; }
.sg-bubble-text :deep(blockquote) { border-left: 3px solid #ff5000; padding-left: 12px; margin: 8px 0; color: #666; }
.sg-bubble-text :deep(table) { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 12px; }
.sg-bubble-text :deep(th) { background: rgba(0, 0, 0, 0.04); padding: 6px 10px; text-align: left; font-weight: 600; }
.sg-bubble-text :deep(td) { padding: 6px 10px; border-top: 1px solid rgba(0, 0, 0, 0.06); }
.sg-bubble-text :deep(hr) { border: none; border-top: 1px solid rgba(0, 0, 0, 0.08); margin: 12px 0; }
.sg-bubble--user .sg-bubble-text :deep(a) { color: #fff; }
.sg-bubble--user .sg-bubble-text :deep(code) { background: rgba(255, 255, 255, 0.2); }
.sg-bubble--user .sg-bubble-text :deep(blockquote) { border-color: rgba(255, 255, 255, 0.5); color: rgba(255, 255, 255, 0.85); }

/* ── 追问 ── */
/* ── 猜你想问卡片 ── */
.sg-followup-prompt-wrap {
  padding: 0 20px 8px;
  max-width: 640px;
  margin: 0 auto;
  width: 100%;
  flex-shrink: 0;
  animation: fup-fade-in 0.3s ease;
}

@keyframes fup-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── 加载动画 ── */
.sg-typing {
  display: flex; align-items: center; gap: 4px; padding: 12px 16px;
  background: #fff; border-radius: 14px; border-top-left-radius: 4px;
}
.sg-typing-dot {
  width: 7px; height: 7px; background: #ccc; border-radius: 50%;
  animation: dot-bounce 1.4s infinite ease-in-out;
}
.sg-typing-dot:nth-child(1) { animation-delay: 0s; }
.sg-typing-dot:nth-child(2) { animation-delay: 0.2s; }
.sg-typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce { 0%, 80%, 100% { transform: scale(0.6); } 40% { transform: scale(1); } }

/* ═══════════════════════════════════════════
   分隔线
   ═══════════════════════════════════════════ */
.sg-divider {
  display: flex; align-items: center; justify-content: center;
  width: 16px; flex-shrink: 0; cursor: col-resize; z-index: 5;
  animation: divider-fade-in 0.3s ease;
}
.sg-divider-handle {
  width: 4px; height: 48px; border-radius: 2px;
  background: rgba(0, 0, 0, 0.15); transition: background 0.15s;
}
.sg-divider:hover .sg-divider-handle { background: rgba(0, 0, 0, 0.3); }
@keyframes divider-fade-in { from { opacity: 0; } to { opacity: 1; } }

/* ═══════════════════════════════════════════
   右侧：内容画布 — 动画滑入
   ═══════════════════════════════════════════ */
.sg-canvas-panel {
  display: flex; flex-direction: column; min-width: 240px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 12px; overflow: hidden;
  animation: canvas-slide-in 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
.sg-canvas-panel--enter {
  animation: canvas-slide-in 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
/* ── Canvas 加载骨架 ── */
.sg-canvas-skeleton {
  padding: 20px 16px; display: flex; flex-direction: column; gap: 12px;
}
.sg-skel-line {
  height: 12px; border-radius: 6px;
  background: linear-gradient(90deg, rgba(0,0,0,0.04) 25%, rgba(0,0,0,0.08) 50%, rgba(0,0,0,0.04) 75%);
  background-size: 200% 100%;
  animation: skel-shimmer 1.5s ease-in-out infinite;
}
.sg-skel-line--title { width: 60%; height: 16px; }
.sg-skel-line--short { width: 80%; }
@keyframes skel-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes canvas-slide-in {
  from {
    opacity: 0;
    transform: translateX(24px);
    clip-path: inset(0 0 0 100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
    clip-path: inset(0 0 0 0);
  }
}

/* ── Canvas Markdown 兜底 ── */
.sg-canvas-markdown-fallback {
  flex: 1; overflow-y: auto; padding: 20px 24px;
}
.sg-canvas-markdown-body {
  font-size: 13px; line-height: 1.7; color: #333;
}
.sg-canvas-empty-state {
  flex: 1; display: flex; align-items: center; justify-content: center;
}

.sg-right-section { display: flex; flex-direction: column; height: 100%; }
.sg-canvas-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid rgba(0, 0, 0, 0.06); flex-shrink: 0;
}
.sg-canvas-title { font-size: 13px; font-weight: 600; color: #333; }
.sg-canvas-count { font-size: 11px; color: #999; background: rgba(0, 0, 0, 0.05); padding: 2px 8px; border-radius: 10px; }

/* ── 商品网格 ── */
.sg-canvas-grid {
  flex: 1; overflow-y: auto; padding: 14px;
  display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; align-content: start;
}
@media (max-width: 1800px) { .sg-canvas-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 1500px) { .sg-canvas-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 1200px) { .sg-canvas-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 900px) { .sg-canvas-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
