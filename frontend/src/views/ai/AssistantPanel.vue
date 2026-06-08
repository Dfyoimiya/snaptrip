<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Close, Promotion } from '@element-plus/icons-vue'
import { adminAgentChatAPI } from '@/apis/agent'
import type { AgentChatResponse } from '@/apis/agent'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  intent?: string
}

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

// Quick prompts
const quickPrompts = [
  '今日销售数据如何？',
  '哪些商品库存不足？',
  '本周订单趋势',
  '会员增长情况',
]

function togglePanel() {
  isOpen.value = !isOpen.value
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
    scrollToBottom()
  }
}

function sendQuickPrompt(prompt: string) {
  inputText.value = prompt
  sendMessage()
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
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
            <span style="margin-left: 6px; font-weight: 600">SnapTrip 管理助手</span>
          </div>
          <el-button link @click="isOpen = false">
            <el-icon><Close /></el-icon>
          </el-button>
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
          <div v-else class="msg-bubble" :class="msg.role">
            <div class="msg-content">{{ msg.content }}</div>
            <div v-if="msg.intent" class="msg-intent">意图: {{ msg.intent }}</div>
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
          placeholder="输入问题..."
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
  width: 400px;
  height: 600px;
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
  max-width: 85%;
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

.msg-intent {
  font-size: 11px;
  color: #86909c;
  margin-top: 4px;
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
</style>
