<script setup lang="ts">
/**
 * ============================================
 * C 端智能客服浮动聊天组件
 * 固定在页面右下角的 AI 客服对话窗口
 * ============================================
 */
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore, type ChatMessage } from '@/stores/chat'
import { useMemberStore } from '@/stores/member'
import { portalCsChatAPI } from '@/apis/cs'
import { renderMarkdown } from '@/utils/markdown'

const router = useRouter()
const chatStore = useChatStore()
const memberStore = useMemberStore()

const inputText = ref('')
const chatContainer = ref<HTMLElement>()

// ── C-end route paths for internal link detection ──────────────────────────

const C_ROUTES = ['/product/', '/order/', '/member/', '/coupons', '/help', '/brand', '/category']

function isCRoute(href: string): boolean {
  return C_ROUTES.some((p) => href.startsWith(p))
}

// ── Quick prompts ──────────────────────────────────────────────────────────

const quickPrompts = [
  '如何退货？',
  '查询我的订单物流',
  '退款政策说明',
  '投诉与建议',
]

// ── Link handling ──────────────────────────────────────────────────────────

function attachLinkHandlers() {
  if (!chatContainer.value) return
  const links = chatContainer.value.querySelectorAll<HTMLAnchorElement>('a[href]')
  links.forEach((link) => {
    if (link.dataset.processed === '1') return
    link.dataset.processed = '1'

    const href = link.getAttribute('href') || ''

    if (isCRoute(href)) {
      link.addEventListener('click', (e) => {
        e.preventDefault()
        chatStore.closeChat()
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

// Re-attach link handlers after messages change
watch(() => chatStore.messages, async () => {
  await nextTick()
  attachLinkHandlers()
  scrollToBottom()
}, { deep: true })

// ── Panel controls ─────────────────────────────────────────────────────────

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  if (!memberStore.isLoggedIn) {
    chatStore.addMessage({
      role: 'system',
      content: '请先登录后再使用客服功能。',
      timestamp: Date.now(),
    })
    return
  }

  chatStore.addMessage({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  chatStore.loading = true

  await nextTick()
  scrollToBottom()

  try {
    const res: any = await portalCsChatAPI({
      message: text,
      session_id: chatStore.sessionId,
    })
    chatStore.addMessage({
      role: 'assistant',
      content: res?.reply || '抱歉，我暂时无法回答这个问题。',
      timestamp: Date.now(),
      intent: res?.intent,
    })
  } catch (err: any) {
    chatStore.addMessage({
      role: 'assistant',
      content: '抱歉，请求失败，请稍后重试。',
      timestamp: Date.now(),
    })
  } finally {
    chatStore.loading = false
    await nextTick()
    attachLinkHandlers()
    scrollToBottom()
  }
}

function sendQuickPrompt(prompt: string) {
  inputText.value = prompt
  sendMessage()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
  if (chatStore.isOpen) {
    nextTick(() => {
      attachLinkHandlers()
      scrollToBottom()
    })
  }
})
</script>

<template>
  <Teleport to="body">
    <!-- Floating FAB button -->
    <button
      v-if="!chatStore.isOpen"
      class="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/30 flex flex-col items-center justify-center cursor-pointer transition-all hover:scale-105 active:scale-95"
      title="在线客服"
      @click="chatStore.openChat"
    >
      <!-- Chat bubble icon -->
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
      <span class="text-[10px] leading-tight mt-0.5">客服</span>
    </button>

    <!-- Chat panel -->
    <div
      v-else
      class="fixed z-40 bg-white shadow-2xl border border-gray-200 flex flex-col overflow-hidden
             md:bottom-6 md:right-6 md:w-[380px] md:h-[520px] md:rounded-xl
             max-md:inset-0 max-md:w-full max-md:h-full max-md:rounded-none"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-red-600 to-red-500 text-white shrink-0">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <span class="font-semibold text-sm">SnapTrip 智能客服</span>
        </div>
        <div class="flex items-center gap-1">
          <button
            class="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
            title="清空对话"
            @click="chatStore.clearMessages"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
          <button
            class="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
            title="关闭"
            @click="chatStore.closeChat"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        <template v-for="(msg, idx) in chatStore.messages" :key="idx">
          <!-- System message -->
          <div v-if="msg.role === 'system'" class="flex justify-center">
            <div class="bg-red-50 text-gray-600 rounded-lg px-3 py-2 text-xs text-center max-w-[90%] leading-relaxed">
              {{ msg.content }}
            </div>
          </div>

          <!-- User / Assistant message -->
          <div v-else class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
            <div class="flex flex-col max-w-[85%]" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
              <div
                class="px-4 py-2.5 text-sm leading-relaxed"
                :class="msg.role === 'user'
                  ? 'bg-red-600 text-white rounded-2xl rounded-br-md'
                  : 'bg-white text-gray-800 rounded-2xl rounded-bl-md shadow-sm border border-gray-100'"
              >
                <div
                  v-if="msg.role === 'assistant'"
                  class="markdown-body"
                  v-html="renderMarkdown(msg.content)"
                />
                <template v-else>{{ msg.content }}</template>
                <div v-if="msg.intent" class="text-[11px] opacity-60 mt-1 pt-1 border-t border-current/20">
                  {{ msg.intent }}
                </div>
              </div>
              <span class="text-[11px] text-gray-400 mt-1 px-1">{{ formatTime(msg.timestamp) }}</span>
            </div>
          </div>
        </template>

        <!-- Loading indicator -->
        <div v-if="chatStore.loading" class="flex justify-start">
          <div class="bg-white text-gray-800 rounded-2xl rounded-bl-md shadow-sm border border-gray-100 px-5 py-3">
            <span class="inline-flex gap-1.5">
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0s" />
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.15s" />
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.3s" />
            </span>
          </div>
        </div>
      </div>

      <!-- Quick prompts -->
      <div
        v-if="chatStore.messages.length <= 1"
        class="flex flex-wrap gap-2 px-4 py-3 border-t border-gray-100 shrink-0"
      >
        <button
          v-for="prompt in quickPrompts"
          :key="prompt"
          class="border border-red-200 text-red-600 hover:bg-red-50 text-xs rounded-full px-3 py-1.5 cursor-pointer transition-colors"
          @click="sendQuickPrompt(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <!-- Input area -->
      <div class="flex items-center gap-2 px-3 py-2.5 border-t border-gray-200 shrink-0 bg-white">
        <input
          v-model="inputText"
          type="text"
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400 placeholder-gray-400"
          :placeholder="memberStore.isLoggedIn ? '输入问题... (Enter 发送)' : '请先登录后再使用客服'"
          :disabled="chatStore.loading || !memberStore.isLoggedIn"
          @keydown="handleKeydown"
        />
        <button
          class="bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors shrink-0"
          :disabled="chatStore.loading || !inputText.trim() || !memberStore.isLoggedIn"
          @click="sendMessage"
        >
          发送
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Markdown body styles ────────────────────────────────────────────────── */

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 8px 0 4px;
  font-weight: 600;
}
.markdown-body :deep(h1) { font-size: 16px; }
.markdown-body :deep(h2) { font-size: 15px; }
.markdown-body :deep(h3) { font-size: 14px; }
.markdown-body :deep(h4) { font-size: 13px; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 18px;
  margin: 4px 0;
}
.markdown-body :deep(li) { margin: 2px 0; }

.markdown-body :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
}
.markdown-body :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  margin: 6px 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 13px;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: #dc2626;
  text-decoration: underline;
  cursor: pointer;
}
.markdown-body :deep(a:hover) { color: #ef4444; }

.markdown-body :deep(blockquote) {
  border-left: 3px solid #dc2626;
  padding-left: 10px;
  margin: 6px 0;
  color: #6b7280;
}

.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #e5e7eb; margin: 8px 0; }
.markdown-body :deep(p) { margin: 4px 0; }
</style>
