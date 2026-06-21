<script setup lang="ts">
/**
 * ============================================
 * 会话历史面板
 * ============================================
 */
import { onMounted } from 'vue'
import { useShoppingGuideStore } from '@/stores/shoppingGuide'

const store = useShoppingGuideStore()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'close'): void
}>()

onMounted(() => {
  store.loadSessions()
})
</script>

<template>
  <div class="ch-panel">
    <div class="ch-header">
      <h3 class="ch-title">历史会话</h3>
      <button class="ch-close" @click="emit('close')">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div v-if="store.sessionsLoading" class="ch-loading">
      <div class="sg-spinner" style="border-color: rgba(0,0,0,0.1); border-top-color: #999;" />
      <span>加载中...</span>
    </div>

    <div v-else-if="!store.sessions.length" class="ch-empty">
      <p>暂无历史会话</p>
    </div>

    <div v-else class="ch-list">
      <button
        v-for="s in store.sessions"
        :key="s.id"
        class="ch-item"
        @click="emit('select', s.id)"
      >
        <div class="ch-item-main">
          <span class="ch-item-summary">{{ s.summary || '新会话' }}</span>
          <span class="ch-item-count">{{ s.messageCount }} 条消息</span>
        </div>
        <span class="ch-item-time">{{ new Date(s.updatedAt).toLocaleDateString() }}</span>
        <button
          class="ch-item-del"
          title="删除"
          @click.stop="store.removeSession(s.id)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        </button>
      </button>
    </div>
  </div>
</template>

<style scoped>
.ch-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.ch-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.ch-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #999;
}

.ch-close:hover {
  background: #f5f5f5;
  color: #333;
}

.ch-loading,
.ch-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: #999;
  font-size: 13px;
}

.ch-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.ch-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  border-radius: 10px;
  transition: background 0.1s;
}

.ch-item:hover {
  background: #f5f5f5;
}

.ch-item-main {
  flex: 1;
  min-width: 0;
}

.ch-item-summary {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ch-item-count {
  font-size: 11px;
  color: #aaa;
}

.ch-item-time {
  font-size: 11px;
  color: #bbb;
  flex-shrink: 0;
}

.ch-item-del {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #ccc;
  flex-shrink: 0;
  opacity: 0;
  transition: all 0.15s;
}

.ch-item:hover .ch-item-del {
  opacity: 1;
}

.ch-item-del:hover {
  background: rgba(255, 80, 0, 0.08);
  color: #ff5000;
}
</style>
