<script setup lang="ts">
/**
 * FollowUpPrompt — 猜你想问交互式追问卡片
 *
 * 在 AI 回复完成后，显示在输入框上方。
 * 支持两种交互模式:
 *  - send: 点击标签直接发送消息
 *  - fill: 点击标签填入输入框，用户可编辑后发送
 *
 * 兼容旧版 string[] followUps（localStorage 迁移）。
 */
import type { FollowUpItem } from '@/apis/shoppingGuide'

defineProps<{
  items: FollowUpItem[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  select: [text: string]
  fill: [text: string]
}>()

function handleClick(item: FollowUpItem, option: string) {
  if (item.action === 'fill') {
    emit('fill', option)
  } else {
    emit('select', option)
  }
}

function normalizeItem(
  item: FollowUpItem | string,
): { text: string; options: string[]; action: 'send' | 'fill' } {
  // Legacy string[] from old localStorage
  if (typeof item === 'string') {
    return { text: '', options: [item], action: 'send' }
  }
  return {
    text: item.text || '',
    options: item.options || [],
    action: item.action || 'send',
  }
}

function hasOptions(item: FollowUpItem | string): boolean {
  const n = normalizeItem(item)
  return n.options.length > 0
}
</script>

<template>
  <div v-if="items.length" class="fup-card">
    <template v-for="(item, idx) in items" :key="idx">
      <div v-if="hasOptions(item)" class="fup-group">
        <p v-if="normalizeItem(item).text" class="fup-text">
          {{ normalizeItem(item).text }}
        </p>
        <div class="fup-chips">
          <button
            v-for="opt in normalizeItem(item).options"
            :key="opt"
            class="fup-chip"
            :disabled="disabled"
            @click="handleClick(item as FollowUpItem, opt)"
          >
            {{ opt }}
          </button>
        </div>
      </div>
      <div v-else class="fup-group">
        <div class="fup-chips">
          <button
            class="fup-chip"
            :disabled="disabled"
            @click="handleClick(item as FollowUpItem, normalizeItem(item).text)"
          >
            {{ normalizeItem(item).text || item }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fup-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.fup-group + .fup-group {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.fup-text {
  font-size: 13px;
  color: #555;
  margin: 0 0 6px;
  font-weight: 500;
}

.fup-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fup-chip {
  padding: 5px 14px;
  font-size: 12px;
  color: #666;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.fup-chip:hover:not(:disabled) {
  border-color: #ff5000;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.05);
}

.fup-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
