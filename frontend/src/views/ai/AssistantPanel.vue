<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Close, Promotion, Delete } from '@element-plus/icons-vue'
import { adminAgentChatAPI } from '@/apis/agent'
import type { AgentChatResponse } from '@/apis/agent'
import { renderMarkdown } from '@/utils/markdown'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  intent?: string
}

const STORAGE_KEY = 'snaptrip_admin_chat_messages'

const router = useRouter()
const isOpen = ref(false)
const inputText = ref('')
const loading = ref(false)
const messages = ref<ChatMessage[]>([
  {
    role: 'system',
    content: '你好！我是 SnapTrip 管理助手。可以问我销售数据、库存预警、订单趋势、会员分析等问题。',
    timestamp: Date.now(),
  },
])
const chatContainer = ref<HTMLElement>()

// ── Admin route paths (for internal link detection) ──────────────────────

const ADMIN_ROUTES = ['/pms', '/oms', '/ums', '/sms', '/cms', '/setting', '/home']

function isAdminPath(href: string): boolean {
  return ADMIN_ROUTES.some(p => href.startsWith(p))
}

// ── Session persistence ───────────────────────────────────────────────────

function loadMessages() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) {
        messages.value = parsed
      }
    }
  } catch { /* ignore corrupt data */ }
}

function saveMessages() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value))
  } catch { /* ignore quota errors */ }
}

function clearMessages() {
  messages.value = [messages.value[0]] // Keep the system greeting
  try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
}

onMounted(loadMessages)
watch(messages, saveMessages, { deep: true })

// ── Link handling ─────────────────────────────────────────────────────────

function attachLinkHandlers() {
  if (!chatContainer.value) return
  const links = chatContainer.value.querySelectorAll<HTMLAnchorElement>('a[href]')
  links.forEach((link) => {
    // Skip already-processed links
    if (link.dataset.processed === '1') return
    link.dataset.processed = '1'

    const href = link.getAttribute('href') || ''

    if (isAdminPath(href)) {
      // Internal admin route — use Vue Router
      link.addEventListener('click', (e) => {
        e.preventDefault()
        isOpen.value = false  // close panel so navigation is visible
        router.push(href)
      })
    } else {
      // External link — open in new tab
      link.setAttribute('target', '_blank')
      link.setAttribute('rel', 'noopener noreferrer')
    }
  })
}

// Re-attach link handlers after messages change
watch(messages, async () => {
  await nextTick()
  attachLinkHandlers()
  scrollToBottom()
}, { deep: true })

// ── Quick prompts ─────────────────────────────────────────────────────────

const quickPrompts = [
  '今日销售数据如何？',
  '哪些商品库存不足？',
  '本周订单趋势',
  '会员增长情况',
]

// ── Panel controls ────────────────────────────────────────────────────────

function togglePanel() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      attachLinkHandlers()
      scrollToBottom()
    })
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  loading.value = true

  await nextTick()
  scrollToBottom()

  try {
    const res = await adminAgentChatAPI({ message: text })
    const data: AgentChatResponse = (res as any).data || res
    messages.value.push({
      role: 'assistant',
      content: data.reply || '抱歉，我暂时无法回答这个问题。',
      timestamp: Date.now(),
      intent: data.intent,
    })
  } catch (err: any) {
    ElMessage.error(err?.message || '请求失败')
    messages.value.push({
      role: 'assistant',
      content: '抱歉，请求失败，请稍后重试。',
      timestamp: Date.now(),
    })
  } finally {
    loading.value = false
    await nextTick()
    attachLinkHandlers()
    scrollToBottom()
  }
}

function sendQuickPrompt(prompt: string) {
  inputText.value = prompt
  sendMessage()
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTo({ top: chatContainer.value.scrollHeight, behavior: 'smooth' })
  }
}

function handleKeydown(e: Event | KeyboardEvent) {
  if (!(e instanceof KeyboardEvent)) return
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="ai-assistant">
    <!-- Floating button -->
    <div v-if="!isOpen" class="ai-fab" @click="togglePanel">
      <el-icon :size="24"><ChatDotRound /></el-icon>
      <span class="fab-label">AI助手</span>
    </div>

    <!-- Chat panel -->
    <el-card v-else class="ai-panel" shadow="always">
      <template #header>
        <div class="panel-header">
          <div class="header-left">
            <el-icon color="#165dff"><Promotion /></el-icon>
            <span class="header-title">SnapTrip 管理助手</span>
          </div>
          <div class="header-actions">
            <el-button link size="small" title="清空对话" @click="clearMessages">
              <el-icon><Delete /></el-icon>
            </el-button>
            <el-button link @click="isOpen = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <!-- Messages -->
      <div ref="chatContainer" class="chat-messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-item"
          :class="msg.role"
        >
          <div v-if="msg.role === 'system'" class="system-msg">
            {{ msg.content }}
          </div>
          <div v-else class="msg-wrapper" :class="msg.role">
            <div class="msg-bubble" :class="msg.role">
              <div
                class="msg-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div v-if="msg.intent" class="msg-intent">{{ msg.intent }}</div>
            </div>
            <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>
        <div v-if="loading" class="message-item assistant">
          <div class="msg-bubble assistant loading-bubble">
            <span class="dot-flashing"></span>
          </div>
        </div>
      </div>

      <!-- Quick prompts -->
      <div v-if="messages.length <= 1" class="quick-prompts">
        <el-button
          v-for="prompt in quickPrompts"
          :key="prompt"
          size="small"
          round
          @click="sendQuickPrompt(prompt)"
        >
          {{ prompt }}
        </el-button>
      </div>

      <!-- Input -->
      <div class="chat-input">
        <el-input
          v-model="inputText"
          placeholder="输入问题... (Enter 发送)"
          :disabled="loading"
          @keydown="handleKeydown"
        >
          <template #append>
            <el-button :loading="loading" :disabled="!inputText.trim()" @click="sendMessage">
              发送
            </el-button>
          </template>
        </el-input>
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.ai-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2000;
}

.ai-fab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #165dff, #4080ff);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(22, 93, 255, 0.35);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 24px rgba(22, 93, 255, 0.45);
  }

  .fab-label {
    font-size: 10px;
    margin-top: 2px;
  }
}

.ai-panel {
  width: 420px;
  height: 640px;
  border-radius: 12px;
  overflow: hidden;

  :deep(.el-card__header) {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e6eb;
  }

  :deep(.el-card__body) {
    padding: 0;
    display: flex;
    flex-direction: column;
    height: calc(100% - 49px);
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-title {
  font-weight: 600;
  font-size: 15px;
}

.header-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: #c1c4cd; border-radius: 2px; }
}

.message-item {
  display: flex;

  &.user { justify-content: flex-end; }
  &.assistant { justify-content: flex-start; }
}

.msg-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 85%;

  &.user { align-items: flex-end; }
  &.assistant { align-items: flex-start; }
}

.system-msg {
  background: #f0f5ff;
  color: #4e5969;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 8px;
  width: 100%;
  text-align: center;
  line-height: 1.6;
}

.msg-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;

  &.user {
    background: #165dff;
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  &.assistant {
    background: #f2f3f5;
    color: #1d2129;
    border-bottom-left-radius: 4px;
  }
}

.msg-content {
  word-break: break-word;
}

.msg-intent {
  font-size: 11px;
  color: #86909c;
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid #e5e6eb;
}

.msg-time {
  font-size: 11px;
  color: #c9cdd4;
  margin-top: 3px;
  padding: 0 4px;
}

.loading-bubble {
  padding: 12px 20px;
}

.dot-flashing {
  position: relative;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #86909c;
  display: block;
  animation: dot-flashing 1s infinite linear alternate;

  &::before, &::after {
    content: '';
    display: inline-block;
    position: absolute;
    top: 0;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #86909c;
    animation: dot-flashing 1s infinite linear alternate;
  }
  &::before { left: -12px; animation-delay: 0s; }
  &::after { left: 12px; animation-delay: 0.5s; }
}

@keyframes dot-flashing {
  0%  { background: #86909c; }
  50%, 100% { background: #c9cdd4; }
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #f2f3f5;
}

.chat-input {
  padding: 12px 16px;
  border-top: 1px solid #e5e6eb;
}

// ── Markdown body styles ──────────────────────────────────────────────────

.markdown-body {
  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin: 8px 0 4px;
    font-weight: 600;
  }
  :deep(h1) { font-size: 17px; }
  :deep(h2) { font-size: 16px; }
  :deep(h3) { font-size: 15px; }
  :deep(h4) { font-size: 14px; }

  :deep(ul), :deep(ol) {
    padding-left: 18px;
    margin: 4px 0;
  }
  :deep(li) { margin: 2px 0; }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 12px;
    font-family: 'SF Mono', Monaco, Consolas, monospace;
  }
  :deep(pre) {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 10px 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
    margin: 6px 0;
    code { background: none; padding: 0; color: inherit; }
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 6px 0;
    font-size: 13px;
    th, td {
      border: 1px solid #dcdfe6;
      padding: 4px 8px;
      text-align: left;
    }
    th { background: #f5f7fa; font-weight: 600; }
  }

  :deep(a) {
    color: #165dff;
    text-decoration: underline;
    cursor: pointer;
    &:hover { color: #4080ff; }
  }

  :deep(blockquote) {
    border-left: 3px solid #165dff;
    padding-left: 10px;
    margin: 6px 0;
    color: #4e5969;
  }

  :deep(strong) { font-weight: 600; }
  :deep(em) { font-style: italic; }
  :deep(hr) { border: none; border-top: 1px solid #e5e6eb; margin: 8px 0; }
  :deep(p) { margin: 4px 0; }
}
</style>
