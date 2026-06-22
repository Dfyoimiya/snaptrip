<script setup lang="ts">
/**
 * ============================================
 * 帮我买 — AI 购物助手页面
 *
 * 参考淘宝 Mac 桌面端帮我买布局：
 *  - 左上：历史对话 + 新对话，历史下拉展开
 *  - 顶部：自动 / 信息搜索 / 商品搜索 三种模式切换
 *  - 左侧：对话区（可左右伸缩）
 *  - 可拖拽分隔线
 *  - 右侧：内容画布 —— 根据模式展示信息搜索结果或商品搜索结果
 *  - 整体受左侧边栏与顶部 Header/TabBar 影响，铺满剩余视口
 * ============================================
 */
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useShoppingGuideStore } from '@/stores/shoppingGuide'
import type { SearchMode } from '@/stores/shoppingGuide'
import type { RecommendedProduct, ShoppingContext } from '@/apis/shoppingGuide'
import type { PmsProduct } from '@/types/product'
import { renderMarkdown } from '@/composables/useMarkdown'
import ProductCard from '@/components/product/ProductCard.vue'
import InfoCardsPanel from '@/components/product/InfoCardsPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useShoppingGuideStore()

/** 模式配置 */
const MODE_LIST: { value: SearchMode; label: string; desc: string }[] = [
  { value: 'auto', label: '自动', desc: 'AI 自动判断信息或商品搜索' },
  { value: 'info', label: '信息搜索', desc: '获取选购建议、攻略、对比信息' },
  { value: 'product', label: '商品搜索', desc: '直接搜索并展示商品列表' },
]

/** 从当前路由构建导购上下文 */
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
// Canvas 分屏比例（始终展示左右两栏）
// ═══════════════════════════════════════════
const splitPercent = ref(36) // 左侧占 36%，右侧 64%
const isDragging = ref(false)
const splitContainer = ref<HTMLElement | null>(null)

const MIN_LEFT_PCT = 24
const MAX_LEFT_PCT = 55

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
  if (historyWrapRef.value && !historyWrapRef.value.contains(target)) {
    historyOpen.value = false
  }
}

onMounted(() => window.addEventListener('click', closeHistoryDropdown))
onUnmounted(() => window.removeEventListener('click', closeHistoryDropdown))

function handleNewSession() {
  store.newSession()
  historyOpen.value = false
}

function handleLoadSession(id: string) {
  store.loadSession(id)
  historyOpen.value = false
}

function formatTime(iso: string | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ═══════════════════════════════════════════
// 模式切换 — 左下角上拉菜单
// ═══════════════════════════════════════════
const modeMenuOpen = ref(false)
const modeMenuRef = ref<HTMLElement | null>(null)

function setMode(mode: SearchMode) {
  store.setSearchMode(mode)
  modeMenuOpen.value = false
}

function toggleModeMenu() {
  modeMenuOpen.value = !modeMenuOpen.value
}

function closeModeMenu(e: MouseEvent) {
  if (modeMenuRef.value && !modeMenuRef.value.contains(e.target as HTMLElement)) {
    modeMenuOpen.value = false
  }
}

const currentModeLabel = computed(() => MODE_LIST.find(m => m.value === store.searchMode)?.label || '自动')

// ═══════════════════════════════════════════
// 滚动
// ═══════════════════════════════════════════
async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.loading, scrollToBottom)
watch(
  () => {
    const msgs = store.messages
    if (!msgs.length) return ''
    const last = msgs[msgs.length - 1]
    return last?.role === 'assistant' && store.loading ? last.content : ''
  },
  scrollToBottom,
)

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
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleFollowUp(q: string) {
  store.sendFollowUp(q, buildContext())
}

// ═══════════════════════════════════════════
// 快捷提示
// ═══════════════════════════════════════════
const QUICK_TIPS = [
  '200 元以内的蓝牙耳机',
  '快过年了，为我推荐年货',
  '学生党性价比高的笔记本',
  '送给女朋友的生日礼物',
]

function useTip(tip: string) {
  input.value = tip
}

// ═══════════════════════════════════════════
// 商品映射
// ═══════════════════════════════════════════
const canvasProducts = computed<PmsProduct[]>(() =>
  store.recommendedProducts.map(mapToPmsProduct),
)

function mapToPmsProduct(p: RecommendedProduct): PmsProduct {
  const productId = p.productId || (p.link ? p.link.split('/').pop() || '' : '')
  return {
    id: productId,
    name: p.name,
    price: p.price,
    originalPrice: p.originalPrice || undefined,
    defaultPic: p.imageUrl || null,
    brandName: p.brandName || null,
    saleCount: p.saleCount || undefined,
    subTitle: null,
    promotionPrice: undefined,
    promotionType: undefined,
    stock: 0,
    categoryId: null,
    newStatus: undefined,
    recommendStatus: undefined,
  }
}

const latestAssistantMessage = computed(() => {
  const msgs = store.messages
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i]?.role === 'assistant') return msgs[i]
  }
  return null
})

const latestInfoCards = computed(() => latestAssistantMessage.value?.infoCards ?? null)

const autoShowProducts = computed(() => canvasProducts.value.length > 0)

function goProductDetail(id: string) {
  if (!id || id === 'undefined') return
  router.push(`/product/${id}`)
}
</script>

<template>
  <div
    ref="splitContainer"
    class="sg-canvas-page"
    :class="{ 'sg-canvas-page--dragging': isDragging }"
  >
    <!-- ═══ 左侧：对话面板 ═══ -->
    <div class="sg-chat-panel" :style="{ width: splitPercent + '%' }">
      <!-- 顶栏：历史 + 新对话 -->
      <div class="sg-left-topbar">
        <div class="sg-left-actions">
          <div ref="historyWrapRef" class="sg-history-wrap">
            <button
              class="sg-action-btn"
              :class="{ active: historyOpen }"
              @click.stop="historyOpen = !historyOpen"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="sg-action-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span>历史</span>
            </button>

            <!-- 历史下拉 -->
            <div v-if="historyOpen" class="sg-history-dropdown">
              <div class="sg-history-dropdown-header">
                <span>历史对话</span>
                <button class="sg-text-btn" @click="store.loadSessions()">刷新</button>
              </div>
              <div v-if="store.sessionsLoading" class="sg-history-empty">加载中...</div>
              <div v-else-if="!store.sessions.length" class="sg-history-empty">暂无历史对话</div>
              <div v-else class="sg-history-list">
                <button
                  v-for="session in store.sessions"
                  :key="session.id"
                  class="sg-history-item"
                  :class="{ active: store.sessionId === session.id }"
                  @click="handleLoadSession(session.id)"
                >
                  <span class="sg-history-title">{{ session.summary || '新对话' }}</span>
                  <span class="sg-history-time">{{ formatTime(session.updatedAt) }}</span>
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

      <!-- 聊天区 -->
      <div ref="msgContainer" class="sg-chat">
        <!-- 空状态 -->
        <div v-if="!store.hasMessages" class="sg-hero">
          <div class="sg-hero-content">
            <h1 class="sg-hero-title">帮我买</h1>
            <p class="sg-hero-subtitle">AI 购物助手，帮你挑选、比价、决策</p>
            <div class="sg-quick-tips">
              <button
                v-for="tip in QUICK_TIPS"
                :key="tip"
                class="sg-quick-tip"
                @click="useTip(tip)"
              >
                {{ tip }}
              </button>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="sg-chat-inner">
          <div
            v-for="(msg, i) in store.messages"
            :key="i"
            class="sg-msg"
            :class="{ 'sg-msg--user': msg.role === 'user' }"
          >
            <div v-if="msg.role === 'assistant'" class="sg-avatar">🤖</div>

            <div class="sg-bubble-col">
              <div class="sg-bubble" :class="{ 'sg-bubble--user': msg.role === 'user' }">
                <div class="sg-bubble-text" v-html="renderMarkdown(msg.content)" />
              </div>

              <!-- 追问 -->
              <div v-if="msg.followUps?.length && msg.role === 'assistant'" class="sg-followups">
                <button
                  v-for="q in msg.followUps"
                  :key="q"
                  class="sg-followup-chip"
                  :disabled="store.loading"
                  @click="handleFollowUp(q)"
                >
                  {{ q }}
                </button>
              </div>
            </div>
          </div>

          <!-- 加载动画 -->
          <div v-if="store.loading && (!store.messages.length || store.messages[store.messages.length - 1]?.role !== 'assistant' || !store.messages[store.messages.length - 1]?.content)" class="sg-msg">
            <div class="sg-avatar">🤖</div>
            <div class="sg-typing">
              <span class="sg-typing-dot" />
              <span class="sg-typing-dot" />
              <span class="sg-typing-dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="sg-footer">
        <div class="sg-footer-inner">
          <div class="sg-input-wrap">
            <textarea
              v-model="input"
              class="sg-input"
              :placeholder="store.searchMode === 'product'
                ? '输入想搜索的商品关键词...'
                : store.searchMode === 'info'
                  ? '输入想了解的信息，如选购攻略、对比...'
                  : '输入你的需求，比如「帮我推荐一款性价比高的手机」...'"
              rows="1"
              :disabled="store.loading"
              @keydown="handleKeydown"
              @input="(e) => {
                const t = (e.target as HTMLTextAreaElement)
                t.style.height = 'auto'
                t.style.height = Math.min(t.scrollHeight, 120) + 'px'
              }"
            />
            <button
              class="sg-send-btn"
              :disabled="!input.trim() || store.loading"
              @click="handleSend"
            >
              <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="sg-send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
              </svg>
              <div v-else class="sg-spinner" />
            </button>
          </div>

          <!-- 左下角模式切换 -->
          <div ref="modeMenuRef" class="sg-mode-picker">
            <button class="sg-mode-current" @click="toggleModeMenu">
              <span>{{ currentModeLabel }}</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="sg-mode-chevron"
                :class="{ open: modeMenuOpen }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
              </svg>
            </button>

            <!-- 上拉选项 -->
            <div v-if="modeMenuOpen" class="sg-mode-popup">
              <button
                v-for="mode in MODE_LIST"
                :key="mode.value"
                class="sg-mode-option"
                :class="{ active: store.searchMode === mode.value }"
                @click="setMode(mode.value)"
              >
                <span class="sg-mode-option-label">{{ mode.label }}</span>
                <span class="sg-mode-option-desc">{{ mode.desc }}</span>
              </button>
            </div>
          </div>

          <div class="sg-footer-hint">内容由 AI 生成，仅供参考</div>
        </div>
      </footer>
    </div>

    <!-- ═══ 可拖拽分隔线 ═══ -->
    <div class="sg-divider" @mousedown="onDividerMouseDown">
      <div class="sg-divider-handle" />
    </div>

    <!-- ═══ 右侧：内容画布 ═══ -->
    <div class="sg-canvas-panel" :style="{ width: (100 - splitPercent) + '%' }">
      <!-- 自动模式 -->
      <template v-if="store.searchMode === 'auto'">
        <div v-if="autoShowProducts" class="sg-right-section">
          <div class="sg-canvas-header">
            <span class="sg-canvas-title">AI 推荐商品</span>
            <span class="sg-canvas-count">{{ canvasProducts.length }} 件</span>
          </div>
          <div class="sg-canvas-grid">
            <ProductCard
              v-for="product in canvasProducts"
              :key="product.id || product.name"
              :product="product"
              @click="goProductDetail(product.id)"
            />
          </div>
        </div>
        <InfoCardsPanel v-else-if="latestInfoCards" :cards="latestInfoCards" />
        <div v-else-if="latestAssistantMessage" class="sg-info-scroll">
          <div class="sg-info-header">AI 智能回答</div>
          <div class="sg-info-body" v-html="renderMarkdown(latestAssistantMessage.content)" />
        </div>
        <div v-else class="sg-canvas-empty">
          <div class="sg-canvas-empty-inner">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <p class="sg-canvas-empty-text">输入需求，AI 将为你自动推荐</p>
            <p class="sg-canvas-empty-hint">自动模式下 AI 会判断展示商品或信息</p>
          </div>
        </div>
      </template>

      <!-- 信息搜索模式 -->
      <template v-else-if="store.searchMode === 'info'">
        <InfoCardsPanel v-if="latestInfoCards" :cards="latestInfoCards" />
        <div v-else-if="latestAssistantMessage" class="sg-info-scroll">
          <div class="sg-info-header">信息搜索结果</div>
          <div class="sg-info-body" v-html="renderMarkdown(latestAssistantMessage.content)" />
        </div>
        <div v-else class="sg-canvas-empty">
          <div class="sg-canvas-empty-inner">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <p class="sg-canvas-empty-text">输入想了解的信息</p>
            <p class="sg-canvas-empty-hint">例如选购攻略、预算建议、商品对比等</p>
          </div>
        </div>
      </template>

      <!-- 商品搜索模式 — 走 Agent 推荐管线 -->
      <template v-else-if="store.searchMode === 'product'">
        <div v-if="autoShowProducts" class="sg-right-section">
          <div class="sg-canvas-header">
            <span class="sg-canvas-title">Agent 推荐商品</span>
            <span class="sg-canvas-count">{{ canvasProducts.length }} 件</span>
          </div>
          <div class="sg-canvas-grid">
            <ProductCard
              v-for="product in canvasProducts"
              :key="product.id || product.name"
              :product="product"
              @click="goProductDetail(product.id)"
            />
          </div>
        </div>
        <div v-else class="sg-canvas-empty">
          <div class="sg-canvas-empty-inner">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p class="sg-canvas-empty-text">输入关键词，AI 为你推荐商品</p>
            <p class="sg-canvas-empty-hint">商品搜索通过 AI 智能推荐，结果展示在右侧</p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   Canvas 页面容器
   宽度由 AppLayout 的 padding-left 自动避让左侧边栏
   高度铺满 HeaderSearch + TabBar 下方的剩余视口
   ═══════════════════════════════════════════ */
.sg-canvas-page {
  display: flex;
  width: 100%;
  height: calc(100vh - 106px - 24px);
  min-height: 500px;
  border-radius: 12px;
  overflow: hidden;
  background: transparent;
}

.sg-canvas-page--dragging {
  cursor: col-resize;
}

/* ═══════════════════════════════════════════
   左侧：对话面板
   ═══════════════════════════════════════════ */
.sg-chat-panel {
  display: flex;
  flex-direction: column;
  min-width: 280px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  overflow: hidden;
}

/* ── 左侧顶栏 ── */
.sg-left-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.sg-left-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sg-history-wrap {
  position: relative;
}

.sg-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #666;
  background: rgba(0, 0, 0, 0.03);
  transition: all 0.15s;
}

.sg-action-btn:hover {
  background: rgba(0, 0, 0, 0.07);
  color: #333;
}

.sg-action-btn.active {
  background: rgba(255, 80, 0, 0.1);
  color: #ff5000;
}

.sg-action-icon {
  width: 14px;
  height: 14px;
}

/* ── 历史下拉 ── */
.sg-history-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 260px;
  max-height: 360px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
  z-index: 30;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sg-history-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.sg-text-btn {
  font-size: 11px;
  color: #999;
  transition: color 0.15s;
}

.sg-text-btn:hover {
  color: #ff5000;
}

.sg-history-list {
  overflow-y: auto;
  padding: 4px;
}

.sg-history-empty {
  padding: 20px 12px;
  text-align: center;
  font-size: 12px;
  color: #bbb;
}

.sg-history-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.15s;
}

.sg-history-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.sg-history-item.active {
  background: rgba(255, 80, 0, 0.08);
}

.sg-history-title {
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sg-history-time {
  font-size: 11px;
  color: #999;
}

/* ── 模式选择器（左下角上拉） ── */
.sg-mode-picker {
  position: relative;
  align-self: flex-start;
  margin-top: 6px;
}

.sg-mode-current {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  color: #999;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 6px;
  transition: all 0.15s;
}

.sg-mode-current:hover {
  color: #666;
  background: rgba(0, 0, 0, 0.06);
}

.sg-mode-chevron {
  width: 12px;
  height: 12px;
  transition: transform 0.2s;
}

.sg-mode-chevron.open {
  transform: rotate(180deg);
}

/* ── 上拉选项弹出层 ── */
.sg-mode-popup {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 220px;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 20;
}

.sg-mode-option {
  display: flex;
  flex-direction: column;
  gap: 1px;
  width: 100%;
  text-align: left;
  padding: 10px 14px;
  transition: background 0.15s;
}

.sg-mode-option:hover {
  background: rgba(0, 0, 0, 0.04);
}

.sg-mode-option.active {
  background: rgba(255, 80, 0, 0.06);
}

.sg-mode-option + .sg-mode-option {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.sg-mode-option-label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.sg-mode-option.active .sg-mode-option-label {
  color: #ff5000;
}

.sg-mode-option-desc {
  font-size: 11px;
  color: #aaa;
  margin-top: 1px;
}

/* ── 空状态 ── */
.sg-hero {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}

.sg-hero-content {
  text-align: center;
  max-width: 520px;
  width: 100%;
}

.sg-hero-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 6px;
}

.sg-hero-subtitle {
  font-size: 15px;
  color: #999;
  margin: 0 0 24px;
}

.sg-quick-tips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.sg-quick-tip {
  padding: 7px 12px;
  font-size: 12px;
  color: #666;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 18px;
  transition: all 0.15s;
}

.sg-quick-tip:hover {
  border-color: #ff5000;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.05);
}

/* ── 对话区 ── */
.sg-chat {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.sg-chat-inner {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 消息 ── */
.sg-msg {
  display: flex;
  gap: 10px;
}

.sg-msg--user {
  flex-direction: row-reverse;
}

.sg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.sg-bubble-col {
  max-width: calc(100% - 45px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sg-bubble {
  padding: 10px 16px;
  border-radius: 14px;
  background: #fff;
  border-top-left-radius: 4px;
  font-size: 13px;
  line-height: 1.65;
  color: #333;
}

.sg-bubble--user {
  background: #ff5000;
  color: #fff;
  border-top-left-radius: 14px;
  border-top-right-radius: 4px;
}

/* ── 输入区 ── */
.sg-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
  padding: 10px 16px 12px;
}

.sg-footer-inner {
  max-width: 100%;
}

.sg-footer-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #bbb;
  text-align: center;
}

.sg-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 7px 7px 7px 16px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 14px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.sg-input-wrap:focus-within {
  border-color: #ff5000;
  background: #fff;
}

.sg-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  line-height: 1.5;
  color: #333;
  resize: none;
  max-height: 100px;
  padding: 3px 0;
}

.sg-input::placeholder {
  color: #bbb;
}

.sg-send-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #ff5000;
  color: #fff;
  flex-shrink: 0;
  transition: all 0.15s;
}

.sg-send-btn:hover:not(:disabled) {
  background: #e64800;
}

.sg-send-btn:disabled {
  background: #e0e0e0;
  color: #bbb;
}

.sg-send-icon {
  width: 16px;
  height: 16px;
}

.sg-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.sg-spinner--dark {
  border-color: rgba(0, 0, 0, 0.15);
  border-top-color: #ff5000;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Markdown ── */
.sg-bubble-text :deep(p) { margin: 0 0 6px; }
.sg-bubble-text :deep(p:last-child) { margin-bottom: 0; }
.sg-bubble-text :deep(ul), .sg-bubble-text :deep(ol) { margin: 4px 0 6px; padding-left: 18px; }
.sg-bubble-text :deep(li) { margin-bottom: 2px; }
.sg-bubble-text :deep(a) { color: #ff5000; text-decoration: underline; }
.sg-bubble-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 12px;
}
.sg-bubble--user .sg-bubble-text :deep(a) { color: #fff; }
.sg-bubble--user .sg-bubble-text :deep(code) { background: rgba(255, 255, 255, 0.2); }

/* ── 追问 ── */
.sg-followups {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sg-followup-chip {
  padding: 6px 12px;
  font-size: 12px;
  color: #666;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  transition: all 0.15s;
}

.sg-followup-chip:hover:not(:disabled) {
  border-color: #ff5000;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.05);
}

.sg-followup-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── 加载动画 ── */
.sg-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 14px;
  border-top-left-radius: 4px;
}

.sg-typing-dot {
  width: 7px;
  height: 7px;
  background: #ccc;
  border-radius: 50%;
  animation: dot-bounce 1.4s infinite ease-in-out;
}

.sg-typing-dot:nth-child(1) { animation-delay: 0s; }
.sg-typing-dot:nth-child(2) { animation-delay: 0.2s; }
.sg-typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

/* ═══════════════════════════════════════════
   分隔线
   ═══════════════════════════════════════════ */
.sg-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  flex-shrink: 0;
  cursor: col-resize;
  z-index: 5;
}

.sg-divider-handle {
  width: 4px;
  height: 48px;
  border-radius: 2px;
  background: rgba(0, 0, 0, 0.15);
  transition: background 0.15s;
}

.sg-divider:hover .sg-divider-handle {
  background: rgba(0, 0, 0, 0.3);
}

/* ═══════════════════════════════════════════
   右侧：内容画布
   ═══════════════════════════════════════════ */
.sg-canvas-panel {
  display: flex;
  flex-direction: column;
  min-width: 240px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  overflow: hidden;
}

.sg-right-section {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sg-canvas-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.sg-canvas-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.sg-canvas-count {
  font-size: 11px;
  color: #999;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 8px;
  border-radius: 10px;
}

/* ── 信息搜索展示 ── */
.sg-info-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.sg-info-header {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.sg-info-body {
  font-size: 13px;
  line-height: 1.8;
  color: #333;
}

.sg-info-body :deep(p) { margin: 0 0 12px; }
.sg-info-body :deep(p:last-child) { margin-bottom: 0; }
.sg-info-body :deep(ul), .sg-info-body :deep(ol) { margin: 8px 0 12px; padding-left: 22px; }
.sg-info-body :deep(li) { margin-bottom: 6px; }
.sg-info-body :deep(h1), .sg-info-body :deep(h2), .sg-info-body :deep(h3) {
  font-weight: 700;
  margin: 18px 0 10px;
  color: #1a1a1a;
}
.sg-info-body :deep(h1) { font-size: 16px; }
.sg-info-body :deep(h2) { font-size: 15px; }
.sg-info-body :deep(h3) { font-size: 14px; }
.sg-info-body :deep(a) { color: #ff5000; text-decoration: underline; }
.sg-info-body :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.sg-info-body :deep(blockquote) {
  margin: 12px 0;
  padding: 10px 14px;
  border-left: 3px solid #ff5000;
  background: rgba(255, 80, 0, 0.05);
  border-radius: 0 8px 8px 0;
  color: #555;
}

/* ── 商品网格 (匹配首页) ── */
.sg-canvas-grid {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
}

@media (max-width: 1800px) {
  .sg-canvas-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1500px) {
  .sg-canvas-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 1200px) {
  .sg-canvas-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .sg-canvas-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* ── 加载 / 空状态 ── */
.sg-canvas-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #999;
  font-size: 13px;
}

.sg-canvas-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  min-width: 200px;
}

.sg-canvas-empty-inner {
  text-align: center;
  color: #ccc;
}

.sg-canvas-empty-text {
  font-size: 14px;
  color: #bbb;
  margin-top: 12px;
}

.sg-canvas-empty-hint {
  font-size: 12px;
  color: #ddd;
  margin-top: 4px;
}
</style>
