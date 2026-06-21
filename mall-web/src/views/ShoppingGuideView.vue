<script setup lang="ts">
/**
 * ============================================
 * 帮我挑 — AI 导购页面
 *
 * 类 ChatGPT 布局：
 *  - 左侧会话列表 (可收起)
 *  - 右侧对话区 + 底部输入
 * ============================================
 */
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useShoppingGuideStore } from '@/stores/shoppingGuide'
import { renderMarkdown } from '@/composables/useMarkdown'

const router = useRouter()
const store = useShoppingGuideStore()
const input = ref('')
const msgContainer = ref<HTMLElement | null>(null)
const sidebarOpen = ref(true)

async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.loading, scrollToBottom)
// 流式输出时，消息内容持续变化但不增加长度，需跟踪最后一条 AI 消息内容
watch(
  () => {
    const msgs = store.messages
    if (!msgs.length) return ''
    const last = msgs[msgs.length - 1]
    if (!last) return ''
    return last.role === 'assistant' && store.loading ? last.content : ''
  },
  scrollToBottom,
)

onMounted(() => {
  store.loadSessions()
  // 默认显示空白新会话，不推送欢迎消息
  store.newSession()
})

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

function handleFollowUp(q: string) {
  store.sendFollowUp(q)
}

function handleProductClick(link: string) {
  if (link.startsWith('/')) {
    router.push(link)
  }
}

async function handleSelectSession(id: string) {
  await store.loadSession(id)
  scrollToBottom()
}

async function handleNewSession() {
  await store.newSession()
  scrollToBottom()
}

async function handleDeleteSession(id: string, e: MouseEvent) {
  e.stopPropagation()
  await store.removeSession(id)
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 86_400_000) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (diff < 7 * 86_400_000) {
    return `${Math.floor(diff / 86_400_000)} 天前`
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="sg-page" :class="{ 'sg-page--sidebar-closed': !sidebarOpen }">
    <!-- ── 左侧会话列表 ── -->
    <aside class="sg-sidebar">
      <div class="sg-sidebar-header">
        <button class="sg-new-session-btn" @click="handleNewSession">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          新建会话
        </button>
      </div>

      <div class="sg-session-list">
        <!-- 加载中 -->
        <div v-if="store.sessionsLoading" class="sg-session-empty">
          <div class="sg-spinner-sm" />
          <span>加载中...</span>
        </div>

        <!-- 无会话 -->
        <div v-else-if="!store.sessions.length" class="sg-session-empty">
          <p class="text-gray-400 text-sm">暂无历史会话</p>
        </div>

        <!-- 会话列表 -->
        <button
          v-for="s in store.sessions"
          :key="s.id"
          class="sg-session-item"
          :class="{ active: s.id === store.sessionId }"
          @click="handleSelectSession(s.id)"
        >
          <div class="sg-session-item-main">
            <span class="sg-session-summary">{{ s.summary || '新会话' }}</span>
            <div class="sg-session-meta">
              <span>{{ s.messageCount }} 条消息</span>
              <span>·</span>
              <span>{{ formatDate(s.updatedAt) }}</span>
            </div>
          </div>
          <button
            class="sg-session-del"
            title="删除"
            @click="(e: MouseEvent) => handleDeleteSession(s.id, e)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </button>
        </button>
      </div>
    </aside>

    <!-- ── 右侧区域 ── -->
    <div class="sg-main">

      <!-- ═══ 空状态：居中输入框 ═══ -->
      <div v-if="!store.hasMessages" class="sg-hero">
        <div class="sg-hero-content">
          <h1 class="sg-hero-title">帮我挑</h1>
          <p class="sg-hero-subtitle">AI 导购助手，帮你找到最合适的商品</p>
          <div class="sg-hero-input-wrap">
            <div class="sg-input-wrap sg-input-wrap--hero">
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
                :disabled="!input.trim() || store.loading"
                @click="handleSend"
              >
                <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="sg-send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
                <div v-else class="sg-spinner" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 有消息时：对话布局 ═══ -->
      <template v-else>
        <!-- 顶栏：侧边栏切换 + 标题 -->
        <div class="sg-topbar">
          <button class="sg-sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <span class="sg-topbar-title">帮我挑 · AI 导购</span>
          <button
            v-if="store.hasMessages"
            class="sg-topbar-action"
            title="新建会话"
            @click="handleNewSession"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </button>
        </div>

        <!-- 消息区 -->
        <div ref="msgContainer" class="sg-chat">
          <div class="sg-chat-inner">
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

                <!-- 商品推荐卡片 -->
                <div v-if="msg.products?.length" class="sg-products">
                  <button
                    v-for="p in msg.products"
                    :key="p.link"
                    class="sg-product-card"
                    @click="handleProductClick(p.link)"
                  >
                    <div class="sg-pcard-body">
                      <span class="sg-pcard-name">{{ p.name }}</span>
                      <div class="sg-pcard-meta">
                        <span class="sg-pcard-price">¥{{ p.price }}</span>
                        <span v-if="p.originalPrice > p.price" class="sg-pcard-original">¥{{ p.originalPrice }}</span>
                        <span v-if="p.discount" class="sg-pcard-discount">{{ p.discount }}</span>
                      </div>
                      <div v-if="p.highlights?.length" class="sg-pcard-tags">
                        <span v-for="h in p.highlights" :key="h" class="sg-pcard-tag">{{ h }}</span>
                      </div>
                    </div>
                    <svg xmlns="http://www.w3.org/2000/svg" class="sg-pcard-arrow" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                    </svg>
                  </button>
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

            <!-- 加载（流式开始前短暂显示打字动画） -->
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
                :disabled="!input.trim() || store.loading"
                @click="handleSend"
              >
                <svg v-if="!store.loading" xmlns="http://www.w3.org/2000/svg" class="sg-send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
                <div v-else class="sg-spinner" />
              </button>
            </div>
            <p class="sg-footer-hint">AI 导购助手，仅供参考 · 每次对话都是一次新的探索</p>
          </div>
        </footer>
      </template>
    </div>
  </div>
</template>

<style scoped>
.sg-page {
  display: flex;
  height: calc(100vh - 220px);
  min-height: 500px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

/* ── 侧边栏 ── */
.sg-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border-right: 1px solid #f0f0f0;
  transition: all 0.25s ease;
  overflow: hidden;
}

.sg-page--sidebar-closed .sg-sidebar {
  width: 0;
  border-right: none;
}

.sg-sidebar-header {
  padding: 12px;
  flex-shrink: 0;
}

.sg-new-session-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 9px 0;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  transition: all 0.15s;
}

.sg-new-session-btn:hover {
  border-color: #ff5000;
  color: #ff5000;
  background: #fff8f5;
}

.sg-session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}

.sg-session-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 16px;
  color: #999;
  font-size: 13px;
}

.sg-spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #e0e0e0;
  border-top-color: #999;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* ── 会话项 ── */
.sg-session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  border-radius: 8px;
  transition: background 0.1s;
  margin-bottom: 2px;
}

.sg-session-item:hover {
  background: #f0f0f0;
}

.sg-session-item.active {
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.sg-session-item-main {
  flex: 1;
  min-width: 0;
}

.sg-session-summary {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 3px;
}

.sg-session-item.active .sg-session-summary {
  color: #ff5000;
}

.sg-session-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #bbb;
}

.sg-session-del {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #ccc;
  flex-shrink: 0;
  opacity: 0;
  transition: all 0.15s;
}

.sg-session-item:hover .sg-session-del {
  opacity: 1;
}

.sg-session-del:hover {
  background: rgba(255, 80, 0, 0.08);
  color: #ff5000;
}

/* ── 主区域 ── */
.sg-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ── 空白状态：居中输入 ── */
.sg-hero {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}

.sg-hero-content {
  text-align: center;
  max-width: 600px;
  width: 100%;
}

.sg-hero-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.sg-hero-subtitle {
  font-size: 15px;
  color: #999;
  margin: 0 0 32px;
}

.sg-hero-input-wrap {
  width: 100%;
}

.sg-input-wrap--hero {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* ── 顶栏 ── */
.sg-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-bottom: 1px solid #f5f5f5;
  flex-shrink: 0;
}

.sg-sidebar-toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #999;
  flex-shrink: 0;
}

.sg-sidebar-toggle:hover {
  background: #f5f5f5;
  color: #333;
}

.sg-topbar-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  flex: 1;
}

.sg-topbar-action {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #999;
}

.sg-topbar-action:hover {
  background: #f5f5f5;
  color: #333;
}

/* ── 对话区 ── */
.sg-chat {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

.sg-chat-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ── 消息 ── */
.sg-msg {
  display: flex;
  gap: 10px;
}

.sg-msg--user {
  flex-direction: row-reverse;
}

/* ── 头像 ── */
.sg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}

/* ── 气泡 ── */
.sg-bubble-col {
  max-width: calc(100% - 50px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sg-bubble {
  padding: 12px 18px;
  border-radius: 16px;
  background: #fff;
  border-top-left-radius: 4px;
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  min-height: 20px;
}

.sg-bubble--user {
  background: #ff5000;
  color: #fff;
  border-top-left-radius: 16px;
  border-top-right-radius: 4px;
}

/* ── Markdown 内容样式 ── */
.sg-bubble-text :deep(p) {
  margin: 0 0 8px;
}
.sg-bubble-text :deep(p:last-child) {
  margin-bottom: 0;
}
.sg-bubble-text :deep(ul),
.sg-bubble-text :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}
.sg-bubble-text :deep(li) {
  margin-bottom: 2px;
}
.sg-bubble-text :deep(a) {
  color: #ff5000;
  text-decoration: underline;
}
.sg-bubble-text :deep(a:hover) {
  color: #e64800;
}
.sg-bubble-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.sg-bubble-text :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 10px 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
}
.sg-bubble-text :deep(pre code) {
  background: none;
  padding: 0;
}
.sg-bubble-text :deep(blockquote) {
  border-left: 3px solid #ff5000;
  padding-left: 12px;
  margin: 8px 0;
  color: #666;
}
.sg-bubble-text :deep(h1),
.sg-bubble-text :deep(h2),
.sg-bubble-text :deep(h3) {
  margin: 10px 0 6px;
  font-weight: 600;
}
.sg-bubble-text :deep(h1) { font-size: 17px; }
.sg-bubble-text :deep(h2) { font-size: 15px; }
.sg-bubble-text :deep(h3) { font-size: 14px; }
.sg-bubble-text :deep(strong) { font-weight: 600; }
.sg-bubble-text :deep(hr) {
  border: none;
  border-top: 1px solid #e5e5e5;
  margin: 10px 0;
}
.sg-bubble--user .sg-bubble-text :deep(a) {
  color: #fff;
  text-decoration: underline;
}
.sg-bubble--user .sg-bubble-text :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}
.sg-bubble--user .sg-bubble-text :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.5);
}

/* ── 商品卡片 ── */
.sg-products {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sg-product-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  text-align: left;
  transition: all 0.15s;
}

.sg-product-card:hover {
  border-color: #ff5000;
  box-shadow: 0 2px 8px rgba(255, 80, 0, 0.08);
}

.sg-pcard-body {
  flex: 1;
  min-width: 0;
}

.sg-pcard-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  display: block;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sg-pcard-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.sg-pcard-price {
  font-size: 17px;
  font-weight: 700;
  color: #ff5000;
}

.sg-pcard-original {
  font-size: 12px;
  color: #bbb;
  text-decoration: line-through;
}

.sg-pcard-discount {
  font-size: 11px;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}

.sg-pcard-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sg-pcard-tag {
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.sg-pcard-arrow {
  width: 20px;
  height: 20px;
  color: #ddd;
  flex-shrink: 0;
}

.sg-product-card:hover .sg-pcard-arrow {
  color: #ff5000;
}

/* ── 追问 ── */
.sg-followups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sg-followup-chip {
  padding: 7px 14px;
  font-size: 13px;
  color: #666;
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 20px;
  transition: all 0.15s;
}

.sg-followup-chip:hover:not(:disabled) {
  border-color: #ff5000;
  color: #ff5000;
  background: #fff8f5;
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
  padding: 14px 18px;
  background: #fff;
  border-radius: 16px;
  border-top-left-radius: 4px;
}

.sg-typing-dot {
  width: 8px;
  height: 8px;
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

/* ── 输入区 ── */
.sg-footer {
  border-top: 1px solid #f0f0f0;
  background: #fff;
  flex-shrink: 0;
}

.sg-footer-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 12px 24px;
}

.sg-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 8px 8px 18px;
  background: #f5f5f5;
  border-radius: 16px;
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
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
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
  width: 18px;
  height: 18px;
}

.sg-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sg-footer-hint {
  text-align: center;
  font-size: 11px;
  color: #bbb;
  margin-top: 8px;
}
</style>
