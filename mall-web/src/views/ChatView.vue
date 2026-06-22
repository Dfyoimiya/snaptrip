<script setup lang="ts">
/**
 * ============================================
 * 客服聊天页 — 用户 ↔ 平台坐席实时对话
 * ============================================
 */
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore, type ChatMessage } from '@/stores/chat'
import { useMemberStore } from '@/stores/member'
import {
  ensureSessionAPI,
  getPortalTicketMessagesAPI,
  sendPortalTicketMessageAPI,
  getPortalTicketStreamUrl,
} from '@/apis/cs'
import { renderMarkdown } from '@/utils/markdown'

const router = useRouter()
const chatStore = useChatStore()
const memberStore = useMemberStore()

const inputText = ref('')
const chatContainer = ref<HTMLElement>()

// ── Connection status ──────────────────────────────────────────────────────

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'

const connectionStatus = ref<ConnectionStatus>('disconnected')
let eventSource: EventSource | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let isDestroyed = false

const statusLabel: Record<ConnectionStatus, string> = {
  disconnected: '未连接',
  connecting: '连接中...',
  connected: '已连接',
}

const statusColorClass: Record<ConnectionStatus, string> = {
  disconnected: 'bg-gray-400',
  connecting: 'bg-yellow-400 animate-pulse',
  connected: 'bg-green-400',
}

// ── Helpers ────────────────────────────────────────────────────────────────

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ── SSE connection ────────────────────────────────────────────────────────

function connectSSE(ticketId: string) {
  closeSSE()
  const url = getPortalTicketStreamUrl(ticketId, memberStore.token as string || undefined)
  connectionStatus.value = 'connecting'

  eventSource = new EventSource(url)

  eventSource.addEventListener('connected', () => {
    connectionStatus.value = 'connected'
  })

  eventSource.addEventListener('new_message', (e: MessageEvent) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.sender_type === 'agent') {
        chatStore.addMessage({
          role: 'assistant',
          content: msg.content,
          timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
        })
        scrollToBottom()
      }
    } catch { /* ignore */ }
  })

  eventSource.addEventListener('error', () => {
    connectionStatus.value = 'disconnected'
    if (!isDestroyed && chatStore.isOpen) {
      reconnectTimer = setTimeout(() => {
        if (!isDestroyed && chatStore.ticketId) connectSSE(chatStore.ticketId)
      }, 5000)
    }
  })
}

function closeSSE() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (eventSource) { eventSource.close(); eventSource = null }
  connectionStatus.value = 'disconnected'
}

// ── Init session ──────────────────────────────────────────────────────────

async function initSession() {
  if (chatStore.ticketId) {
    await loadHistory(chatStore.ticketId)
    connectSSE(chatStore.ticketId)
    return
  }
  try {
    const res = await ensureSessionAPI()
    const data = res.data
    if (data?.id) {
      chatStore.setTicketId(data.id)
      await loadHistory(data.id)
      connectSSE(data.id)
    }
  } catch {
    chatStore.addMessage({ role: 'system', content: '客服系统暂时不可用，请稍后重试。', timestamp: Date.now() })
  }
}

async function loadHistory(ticketId: string) {
  try {
    const res = await getPortalTicketMessagesAPI(ticketId)
    const msgs = res.data?.messages || []
    msgs.forEach((msg: any) => {
      const role = msg.sender_type === 'agent' ? 'assistant' as const : 'user' as const
      const exists = chatStore.messages.some(m => m.role === role && m.content === msg.content)
      if (!exists) {
        chatStore.addMessage({
          role,
          content: msg.content,
          timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
        })
      }
    })
    scrollToBottom()
  } catch { /* silent */ }
}

// ── Send message ──────────────────────────────────────────────────────────

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  chatStore.addMessage({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  chatStore.loading = true
  scrollToBottom()

  if (!chatStore.ticketId) {
    try {
      const res = await ensureSessionAPI()
      if (res.data?.id) chatStore.setTicketId(res.data.id)
    } catch {
      chatStore.loading = false
      return
    }
  }

  try {
    await sendPortalTicketMessageAPI(chatStore.ticketId!, text)
  } catch {
    chatStore.addMessage({ role: 'assistant', content: '消息发送失败，请稍后重试。', timestamp: Date.now() })
  } finally {
    chatStore.loading = false
    scrollToBottom()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(() => {
  isDestroyed = false
  chatStore.isOpen = true  // 页面级打开状态
  if (chatStore.messages.length <= 1) {
    chatStore.clearMessages()
  }
  initSession()
})

onUnmounted(() => {
  isDestroyed = true
  chatStore.isOpen = false
  closeSSE()
})
</script>

<template>
  <div class="chat-page">
    <!-- Header -->
    <header class="chat-header">
      <button class="back-btn" @click="router.back()" title="返回">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="header-center">
        <h1 class="header-title">客服消息</h1>
        <div class="connection-indicator">
          <span class="status-dot" :class="statusColorClass[connectionStatus]" />
          <span class="status-text">{{ statusLabel[connectionStatus] }}</span>
        </div>
      </div>
      <div class="header-spacer" />
    </header>

    <!-- Messages -->
    <div ref="chatContainer" class="chat-body">
      <template v-for="(msg, idx) in chatStore.messages" :key="idx">
        <!-- System message -->
        <div v-if="msg.role === 'system'" class="message-system">
          {{ msg.content }}
        </div>

        <!-- User / Assistant -->
        <div v-else class="message-row" :class="msg.role === 'user' ? 'message-out' : 'message-in'">
          <div class="message-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-agent'">
            <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)" />
            <template v-else>{{ msg.content }}</template>
          </div>
          <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
        </div>
      </template>

      <!-- Loading -->
      <div v-if="chatStore.loading" class="message-row message-in">
        <div class="message-bubble bubble-agent typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-footer">
      <div class="input-row">
        <input
          v-model="inputText"
          type="text"
          class="chat-input"
          placeholder="输入消息... (Enter 发送)"
          :disabled="chatStore.loading"
          @keydown="handleKeydown"
        />
        <button
          class="send-btn"
          :disabled="chatStore.loading || !inputText.trim()"
          @click="sendMessage"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============================================
   Chat Page Layout
   ============================================ */
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.chat-header {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
  gap: 12px;
}

.back-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  color: #555;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}
.back-btn:hover { background: #f0f0f0; }

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f1f1f;
  margin: 0;
}

.connection-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  font-size: 11px;
  color: #999;
}

.header-spacer { width: 36px; flex-shrink: 0; }

/* ── Body ───────────────────────────────────────────────────────────────── */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-system {
  text-align: center;
  font-size: 12px;
  color: #999;
  background: rgba(0,0,0,0.04);
  border-radius: 8px;
  padding: 6px 16px;
  max-width: 70%;
  margin: 8px auto;
  line-height: 1.5;
}

.message-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 70%;
}

.message-out {
  align-self: flex-end;
  align-items: flex-end;
}

.message-in {
  align-self: flex-start;
  align-items: flex-start;
}

.message-bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.bubble-user {
  background: #ff5000;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-agent {
  background: #fff;
  color: #333;
  border: 1px solid #eee;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.message-time {
  font-size: 10px;
  color: #bbb;
  padding: 0 4px;
}

/* ── Typing dots ────────────────────────────────────────────────────────── */
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 14px 18px;
}
.typing-dots span {
  width: 7px;
  height: 7px;
  background: #bbb;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
.typing-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* ── Footer ─────────────────────────────────────────────────────────────── */
.chat-footer {
  flex-shrink: 0;
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #eee;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.chat-input {
  flex: 1;
  height: 42px;
  padding: 0 14px;
  border: 1px solid #e0e0e0;
  border-radius: 21px;
  font-size: 14px;
  color: #333;
  outline: none;
  transition: border-color 0.15s;
  background: #f8f8f8;
}
.chat-input:focus { border-color: #ff5000; background: #fff; }
.chat-input::placeholder { color: #bbb; }

.send-btn {
  height: 42px;
  padding: 0 22px;
  background: #ff5000;
  color: #fff;
  border: none;
  border-radius: 21px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}
.send-btn:hover { background: #e64600; }
.send-btn:disabled { background: #ffb899; cursor: not-allowed; }

/* ── Markdown ───────────────────────────────────────────────────────────── */
.markdown-body :deep(p) { margin: 0; }
.markdown-body :deep(p + p) { margin-top: 6px; }
.markdown-body :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
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
.markdown-body :deep(a) { color: #ff5000; }
</style>
