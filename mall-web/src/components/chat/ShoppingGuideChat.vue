<script setup lang="ts">
/**
 * ============================================
 * 帮我挑 — AI 导购聊天面板
 *
 * 侧边滑出式聊天窗口：
 *  - 对话气泡 (用户 / AI)
 *  - 商品推荐卡片
 *  - 追问快捷按钮
 *  - 会话管理 (新建 / 历史)
 * ============================================
 */
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useShoppingGuideStore, type RecommendedProduct } from '@/stores/shoppingGuide'
import ChatHistory from './ChatHistory.vue'

const router = useRouter()
const store = useShoppingGuideStore()

const input = ref('')
const msgContainer = ref<HTMLElement | null>(null)
const showHistory = ref(false)

// ── 滚动到底部 ──
async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.loading, scrollToBottom)

// ── 发送 ──
function handleSend() {
  if (!input.value.trim() || store.loading) return
  store.sendMessage(input.value)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// ── 点击追问 ──
function handleFollowUp(q: string) {
  store.sendFollowUp(q)
}

// ── 点击商品链接 ──
function handleProductClick(link: string) {
  store.closeChat()
  if (link.startsWith('/')) {
    router.push(link)
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩 -->
    <div
      v-if="store.isOpen"
      class="sg-overlay"
      @click="store.closeChat"
    />

    <!-- 聊天面板 -->
    <div
      v-if="store.isOpen"
      class="sg-panel"
      :class="{ 'sg-panel--history': showHistory }"
    >
      <!-- 头部 -->
      <header class="sg-header">
        <div class="sg-header-left">
          <button class="sg-header-btn" title="会话历史" @click="showHistory = !showHistory">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </button>
          <h2 class="sg-title">帮我挑</h2>
          <span class="sg-subtitle">AI 导购</span>
        </div>
        <div class="sg-header-right">
          <button class="sg-header-btn" title="新建会话" @click="store.newSession()">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </button>
          <button class="sg-header-btn" title="关闭" @click="store.closeChat">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </header>

      <div class="sg-body">
        <!-- 历史会话列表 -->
        <ChatHistory
          v-if="showHistory"
          @select="(id: string) => { store.loadSession(id); showHistory = false }"
          @close="showHistory = false"
        />

        <!-- 消息区域 -->
        <div
          v-else
          ref="msgContainer"
          class="sg-messages"
        >
          <!-- 空状态引导 -->
          <div v-if="!store.hasMessages" class="sg-empty">
            <div class="sg-empty-icon">🛍️</div>
            <p class="sg-empty-title">AI 导购助手</p>
            <p class="sg-empty-desc">告诉我你的需求，我帮你找到最合适的商品</p>
            <div class="sg-empty-hints">
              <button
                v-for="q in ['推荐一款适合学生的笔记本', '200 元以内的蓝牙耳机', '最近有什么优惠活动']"
                :key="q"
                class="sg-hint-chip"
                @click="handleFollowUp(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <!-- 消息列表 -->
          <div
            v-for="(msg, i) in store.messages"
            :key="i"
            class="sg-msg"
            :class="{
              'sg-msg--user': msg.role === 'user',
              'sg-msg--system': msg.role === 'system',
            }"
          >
            <!-- AI 头像 -->
            <div v-if="msg.role === 'assistant'" class="sg-avatar sg-avatar--ai">
              🤖
            </div>

            <div class="sg-bubble-wrap">
              <!-- 消息气泡 -->
              <div class="sg-bubble" :class="{ 'sg-bubble--user': msg.role === 'user' }">
                <div class="sg-bubble-text" v-html="msg.content.replace(/\n/g, '<br>')" />
              </div>

              <!-- 推荐商品卡片 -->
              <div v-if="msg.products?.length" class="sg-products">
                <div
                  v-for="p in msg.products"
                  :key="p.link"
                  class="sg-product-card"
                  @click="handleProductClick(p.link)"
                >
                  <div class="sg-product-info">
                    <div class="sg-product-name">{{ p.name }}</div>
                    <div class="sg-product-meta">
                      <span class="sg-product-price">¥{{ p.price }}</span>
                      <span v-if="p.originalPrice > p.price" class="sg-product-original">¥{{ p.originalPrice }}</span>
                      <span v-if="p.discount" class="sg-product-discount">{{ p.discount }}</span>
                    </div>
                    <div v-if="p.highlights?.length" class="sg-product-tags">
                      <span v-for="h in p.highlights" :key="h" class="sg-product-tag">{{ h }}</span>
                    </div>
                  </div>
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                  </svg>
                </div>
              </div>

              <!-- 追问按钮 -->
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

          <!-- 加载指示器 -->
          <div v-if="store.loading" class="sg-msg">
            <div class="sg-avatar sg-avatar--ai">🤖</div>
            <div class="sg-typing">
              <span class="sg-typing-dot" />
              <span class="sg-typing-dot" />
              <span class="sg-typing-dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 (隐藏于历史视图) -->
      <footer v-if="!showHistory" class="sg-footer">
        <div class="sg-input-wrap">
          <textarea
            v-model="input"
            class="sg-input"
            placeholder="输入你的需求，比如「帮我推荐一款性价比高的手机」..."
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
            :class="{ loading: store.loading }"
            :disabled="!input.trim() || store.loading"
            @click="handleSend"
          >
            <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
            <div v-else class="sg-spinner" />
          </button>
        </div>
      </footer>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── 遮罩 ── */
.sg-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.25);
  z-index: 100;
}

/* ── 面板 ── */
.sg-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 440px;
  max-width: 100vw;
  background: #ffffff;
  z-index: 101;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
  animation: sg-slide-in 0.25s ease-out;
}

@keyframes sg-slide-in {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

/* ── 头部 ── */
.sg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.sg-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sg-title {
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
}

.sg-subtitle {
  font-size: 11px;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.08);
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.sg-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sg-header-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #666;
  transition: all 0.15s;
}

.sg-header-btn:hover {
  background: #f5f5f5;
  color: #1a1a1a;
}

/* ── 主体 ── */
.sg-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sg-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 空状态 ── */
.sg-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  flex: 1;
}

.sg-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.sg-empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 6px;
}

.sg-empty-desc {
  font-size: 13px;
  color: #999;
  margin-bottom: 20px;
}

.sg-empty-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 360px;
}

.sg-hint-chip {
  padding: 8px 14px;
  font-size: 13px;
  color: #666;
  background: #f5f5f5;
  border-radius: 16px;
  transition: all 0.15s;
}

.sg-hint-chip:hover {
  background: #ff5000;
  color: #fff;
}

/* ── 消息行 ── */
.sg-msg {
  display: flex;
  gap: 8px;
  max-width: 100%;
}

.sg-msg--user {
  flex-direction: row-reverse;
}

.sg-msg--system {
  justify-content: center;
}

/* ── 头像 ── */
.sg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.sg-avatar--ai {
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
}

/* ── 气泡 ── */
.sg-bubble-wrap {
  max-width: calc(100% - 48px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sg-bubble {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  background: #f5f5f5;
  border-top-left-radius: 4px;
}

.sg-bubble--user {
  background: #ff5000;
  color: #fff;
  border-top-left-radius: 14px;
  border-top-right-radius: 4px;
}

/* ── 商品卡片 ── */
.sg-products {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sg-product-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  gap: 8px;
}

.sg-product-card:hover {
  border-color: #ff5000;
  background: #fff8f5;
}

.sg-product-info {
  flex: 1;
  min-width: 0;
}

.sg-product-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.sg-product-meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
}

.sg-product-price {
  font-size: 15px;
  font-weight: 700;
  color: #ff5000;
}

.sg-product-original {
  font-size: 11px;
  color: #bbb;
  text-decoration: line-through;
}

.sg-product-discount {
  font-size: 10px;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.08);
  padding: 0 5px;
  border-radius: 4px;
}

.sg-product-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sg-product-tag {
  font-size: 10px;
  color: #888;
  background: #f0f0f0;
  padding: 1px 6px;
  border-radius: 4px;
}

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
  background: #f8f8f8;
  border: 1px solid #eee;
  border-radius: 14px;
  transition: all 0.15s;
}

.sg-followup-chip:hover:not(:disabled) {
  border-color: #ff5000;
  color: #ff5000;
  background: #fff8f5;
}

.sg-followup-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 加载动画 ── */
.sg-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 14px;
  border-top-left-radius: 4px;
}

.sg-typing-dot {
  width: 7px;
  height: 7px;
  background: #ccc;
  border-radius: 50%;
  animation: sg-dot-bounce 1.4s infinite ease-in-out;
}

.sg-typing-dot:nth-child(1) { animation-delay: 0s; }
.sg-typing-dot:nth-child(2) { animation-delay: 0.2s; }
.sg-typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes sg-dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

/* ── 输入区 ── */
.sg-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.sg-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f5f5f5;
  border-radius: 14px;
  padding: 6px 6px 6px 14px;
  border: 1.5px solid transparent;
  transition: border-color 0.2s;
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
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  resize: none;
  max-height: 120px;
  padding: 4px 0;
}

.sg-input::placeholder {
  color: #bbb;
}

.sg-send-btn {
  width: 36px;
  height: 36px;
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
  background: #ddd;
  color: #aaa;
}

.sg-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: sg-spin 0.6s linear infinite;
}

@keyframes sg-spin {
  to { transform: rotate(360deg); }
}
</style>
