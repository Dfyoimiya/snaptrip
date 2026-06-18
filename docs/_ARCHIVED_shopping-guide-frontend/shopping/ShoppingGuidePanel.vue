<script setup lang="ts">
/**
 * ============================================
 * 导购 Agent 侧边面板 — 抽屉式揭露
 *
 * 层次关系：
 * - AI 面板是底层（暖木色调背景层）
 * - 商品页是上层（抽屉面）
 * - 打开时商品页左移，露出底层的 AI 面板
 * - 无遮罩，纯粹的空间层次感
 * ============================================
 */
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useShoppingGuideStore } from '@/stores/shoppingGuide'
import { useMemberStore } from '@/stores/member'
import { shoppingGuideChatAPI } from '@/apis/shoppingGuide'
import ProductCardInline from './ProductCardInline.vue'

const router = useRouter()
const guideStore = useShoppingGuideStore()
const memberStore = useMemberStore()

const inputText = ref('')
const chatContainer = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()

const quickPrompts = [
  '帮我推荐一款蓝牙耳机',
  '今天有什么优惠活动？',
  '推荐送女朋友的礼物',
  '有什么性价比高的运动鞋？',
]

// ── Markdown ───────────────────────────────────────────────────────────────

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="link">$1</a>'
  )
  html = html.replace(/\n\n/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')
  return '<p>' + html + '</p>'
}

// ── Product links ──────────────────────────────────────────────────────────

function extractProductLinks(text: string): Array<{ name: string; url: string; id: string }> {
  const links: Array<{ name: string; url: string; id: string }> = []
  // Match relative /product/xxx or absolute https://shop.snaptrip.com/product/xxx
  const regex = /\[([^\]]+)\]\(((?:https?:\/\/shop\.snaptrip\.com)?\/product\/([^)]+))\)/g
  let match
  while ((match = regex.exec(text)) !== null) {
    const href = match[2]
    const fullUrl = href.startsWith('/') ? href : href
    links.push({ name: match[1], url: fullUrl, id: match[3] })
  }
  return links
}

// ── Internal link routing ──────────────────────────────────────────────────

const INTERNAL_ROUTES = ['/product/', '/member/', '/coupons', '/brand', '/category', '/search']

function isInternalRoute(href: string): boolean {
  // Strip domain if absolute URL to our own shop
  const cleaned = href.replace(/^https?:\/\/shop\.snaptrip\.com/, '')
  return INTERNAL_ROUTES.some((p) => cleaned.startsWith(p))
}

function attachLinkHandlers() {
  if (!chatContainer.value) return
  const links = chatContainer.value.querySelectorAll<HTMLAnchorElement>('a[href]')
  links.forEach((link) => {
    if (link.dataset.processed === '1') return
    link.dataset.processed = '1'
    const href = link.getAttribute('href') || ''
    if (isInternalRoute(href)) {
      link.addEventListener('click', (e) => {
        e.preventDefault()
        router.push(href)
      })
    } else {
      link.setAttribute('target', '_blank')
      link.setAttribute('rel', 'noopener noreferrer')
    }
  })
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTo({ top: chatContainer.value.scrollHeight, behavior: 'smooth' })
  }
}

watch(
  () => guideStore.messages,
  async () => {
    await nextTick()
    attachLinkHandlers()
    scrollToBottom()
  },
  { deep: true },
)

// ── Body class ─────────────────────────────────────────────────────────────

watch(
  () => guideStore.isOpen,
  (open) => {
    if (open) {
      document.body.classList.add('sg-panel-open')
    } else {
      document.body.classList.remove('sg-panel-open')
    }
  },
)

onUnmounted(() => {
  document.body.classList.remove('sg-panel-open')
})

// ── Keyboard ───────────────────────────────────────────────────────────────

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'g') {
    e.preventDefault()
    guideStore.togglePanel()
  }
  if (e.key === 'Escape' && guideStore.isOpen) {
    guideStore.closePanel()
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

// ── Send ───────────────────────────────────────────────────────────────────

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || guideStore.loading) return

  if (!memberStore.isLoggedIn) {
    guideStore.addMessage({
      role: 'system',
      content: '请先登录后再使用导购功能。',
      timestamp: Date.now(),
    })
    return
  }

  guideStore.addMessage({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  guideStore.loading = true

  await nextTick()
  scrollToBottom()

  try {
    const res = await shoppingGuideChatAPI({
      message: text,
      sessionId: guideStore.sessionId,
    })

    guideStore.addMessage({
      role: 'assistant',
      content: res.reply,
      timestamp: Date.now(),
    })

    if (res.followUpQuestions?.length) {
      guideStore.setFollowUpQuestions(res.followUpQuestions)
    } else {
      guideStore.clearFollowUpQuestions()
    }

    if (res.sessionId) {
      guideStore.sessionId = res.sessionId
    }
  } catch (err: any) {
    guideStore.addMessage({
      role: 'system',
      content: `抱歉，出现了一些问题：${err.message || '网络错误'}`,
      timestamp: Date.now(),
    })
  } finally {
    guideStore.loading = false
    await nextTick()
    scrollToBottom()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- 抽屉式面板：滑块动画与商品页左移同步 -->
    <Transition name="sg-panel">
      <aside
        v-if="guideStore.isOpen"
        class="sg-panel"
      >
        <!-- Header -->
        <div class="sg-header">
          <div class="sg-header-title">
            <svg class="sg-header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              <path d="M8 9h8M8 13h6" stroke-width="1.5"/>
            </svg>
            <span>导购助手</span>
          </div>
          <div class="sg-header-actions">
            <button
              class="sg-header-btn"
              title="新会话"
              @click="guideStore.clearMessages()"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
                <path d="M12 5v14M5 12h14"/>
              </svg>
            </button>
            <button
              class="sg-header-btn"
              title="关闭 (Esc)"
              @click="guideStore.closePanel()"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
                <path d="M18 6 6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div ref="chatContainer" class="sg-messages">
          <template v-for="(msg, idx) in guideStore.messages" :key="idx">
            <div v-if="msg.role === 'system'" class="sg-msg-system">
              {{ msg.content }}
            </div>

            <div v-else-if="msg.role === 'user'" class="sg-msg-user">
              <div class="sg-msg-user-bubble">
                {{ msg.content }}
              </div>
            </div>

            <div v-else class="sg-msg-assistant">
              <div
                class="sg-msg-assistant-content"
                v-html="renderMarkdown(msg.content)"
              />
              <ProductCardInline
                v-for="link in extractProductLinks(msg.content)"
                :key="link.id"
                :name="link.name"
                :product-id="link.id"
                :url="link.url"
              />
            </div>
          </template>

          <div v-if="guideStore.loading" class="sg-typing">
            <span class="sg-typing-dot" />
            <span class="sg-typing-dot" />
            <span class="sg-typing-dot" />
          </div>
        </div>

        <!-- 追问 -->
        <div
          v-if="guideStore.followUpQuestions.length > 0 && !guideStore.loading"
          class="sg-followups"
        >
          <button
            v-for="(q, i) in guideStore.followUpQuestions"
            :key="i"
            class="sg-followup-chip"
            @click="inputText = q; sendMessage()"
          >
            {{ q }}
          </button>
        </div>

        <!-- 快捷提示 -->
        <div
          v-else-if="guideStore.messages.length <= 1 && !guideStore.loading"
          class="sg-quick-prompts"
        >
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="sg-quick-prompt"
            @click="inputText = prompt; sendMessage()"
          >
            {{ prompt }}
          </button>
        </div>

        <!-- 输入 -->
        <div class="sg-input-area">
          <div class="sg-input-wrapper">
            <input
              ref="inputRef"
              v-model="inputText"
              type="text"
              class="sg-input"
              placeholder="告诉我你想买什么..."
              :disabled="guideStore.loading"
              @keydown="handleKeydown"
            />
            <button
              class="sg-send-btn"
              :class="{ 'sg-send-btn--active': inputText.trim() && !guideStore.loading }"
              :disabled="!inputText.trim() || guideStore.loading"
              @click="sendMessage()"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
                <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style>
/* ── 商品页抽屉式左移，露出底层 AI 面板 ────────────────────────────────── */

#app > .main-layout {
  margin-right: 0;
  border-radius: 0;
  overflow: visible;
  box-shadow: none;
  transition:
    margin-right 0.35s cubic-bezier(0.4, 0, 0.2, 1),
    border-radius 0.35s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

body.sg-panel-open #app > .main-layout {
  margin-right: min(35vw, 480px);
  border-radius: 0 16px 16px 0;
  overflow: clip;
  /*
   * 商品页右边缘向右投射阴影到下层 AI 面板上
   * 多层营造 Apple 式层级感
   */
  box-shadow:
    2px 0 8px rgba(60, 30, 10, 0.06),
    8px 0 24px rgba(60, 30, 10, 0.05),
    16px 0 48px rgba(60, 30, 10, 0.03);
}
</style>

<style scoped>
/* ── 面板本体 — 暖木调底层 ──────────────────────────────────────────────── */

.sg-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: min(35vw, 480px);
  min-width: 360px;
  height: 100vh;
  z-index: 41;
  display: flex;
  flex-direction: column;
  background: #faf7f3;
  border-left: 1px solid #e5ddd4;
}

.sg-panel-enter-active,
.sg-panel-leave-active {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.sg-panel-enter-from,
.sg-panel-leave-to {
  transform: translateX(100%);
}

.sg-panel-enter-to,
.sg-panel-leave-from {
  transform: translateX(0);
}

/* ── Header ──────────────────────────────────────────────────────────────── */

.sg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #ede4da;
  flex-shrink: 0;
  background: #f5f0ea;
}

.sg-header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #3d3228;
}

.sg-header-icon {
  width: 20px;
  height: 20px;
  color: #a0724a;
}

.sg-header-actions {
  display: flex;
  gap: 4px;
}

.sg-header-btn {
  padding: 6px;
  border-radius: 8px;
  color: #a09080;
  transition: all 0.15s;
}

.sg-header-btn:hover {
  background: #e8ddd0;
  color: #5d4e3a;
}

/* ── Messages ────────────────────────────────────────────────────────────── */

.sg-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sg-msg-system {
  text-align: center;
  font-size: 13px;
  color: #a09080;
  padding: 8px 16px;
  background: #f5f0ea;
  border-radius: 10px;
  max-width: 85%;
  margin: 0 auto;
}

.sg-msg-user {
  display: flex;
  justify-content: flex-end;
}

.sg-msg-user-bubble {
  max-width: 80%;
  padding: 10px 16px;
  background: #a0724a;
  color: #ffffff;
  border-radius: 16px 16px 4px 16px;
  font-size: 14px;
  line-height: 1.5;
}

.sg-msg-assistant {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sg-msg-assistant-content {
  font-size: 14px;
  line-height: 1.65;
  color: #4a3f35;
}

.sg-msg-assistant-content :deep(p) {
  margin-bottom: 8px;
}

.sg-msg-assistant-content :deep(p:last-child) {
  margin-bottom: 0;
}

.sg-msg-assistant-content :deep(strong) {
  font-weight: 600;
  color: #2d2520;
}

.sg-msg-assistant-content :deep(.link) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.sg-msg-assistant-content :deep(code) {
  background: #f0ece6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

/* ── Typing ──────────────────────────────────────────────────────────────── */

.sg-typing {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.sg-typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c4b8a8;
  animation: sg-bounce 1.2s infinite ease-in-out;
}

.sg-typing-dot:nth-child(2) { animation-delay: 0.2s; }
.sg-typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes sg-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ── Follow-ups ──────────────────────────────────────────────────────────── */

.sg-followups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 20px 8px;
  border-top: 1px solid #ede4da;
  flex-shrink: 0;
}

.sg-followup-chip {
  padding: 6px 14px;
  border-radius: 20px;
  background: #f5f0ea;
  border: 1px solid #ddd2c4;
  font-size: 13px;
  color: #6b5540;
  transition: all 0.15s;
  white-space: nowrap;
}

.sg-followup-chip:hover {
  background: #a0724a;
  border-color: #a0724a;
  color: #ffffff;
}

/* ── Quick prompts ───────────────────────────────────────────────────────── */

.sg-quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 20px 8px;
  border-top: 1px solid #ede4da;
  flex-shrink: 0;
}

.sg-quick-prompt {
  padding: 6px 14px;
  border-radius: 20px;
  background: #f5f0ea;
  border: 1px solid #ddd2c4;
  font-size: 13px;
  color: #5d4e3a;
  transition: all 0.15s;
  white-space: nowrap;
}

.sg-quick-prompt:hover {
  background: #e8ddd0;
  border-color: #c4b8a8;
  color: #3d3026;
}

/* ── Input ───────────────────────────────────────────────────────────────── */

.sg-input-area {
  padding: 12px 20px 16px;
  border-top: 1px solid #ede4da;
  flex-shrink: 0;
  background: #f5f0ea;
}

.sg-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 16px;
  background: #faf7f3;
  border: 1px solid #ddd2c4;
  border-radius: 24px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.sg-input-wrapper:focus-within {
  border-color: #a0724a;
  box-shadow: 0 0 0 2px rgba(160, 114, 74, 0.1);
}

.sg-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  color: #3d3228;
  background: transparent;
}

.sg-input::placeholder {
  color: #b8a898;
}

.sg-send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #ede4da;
  color: #a09080;
  transition: all 0.15s;
  flex-shrink: 0;
}

.sg-send-btn--active {
  background: #a0724a;
  color: #ffffff;
}

.sg-send-btn--active:hover {
  background: #8a5f3c;
}
</style>
