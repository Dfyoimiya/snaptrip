<script setup lang="ts">
/**
 * ============================================
 * "帮我挑" 浮动入口按钮
 * ============================================
 */
import { useShoppingGuideStore } from '@/stores/shoppingGuide'

const store = useShoppingGuideStore()
</script>

<template>
  <button
    class="sg-entry"
    :class="{ active: store.isOpen }"
    title="AI 导购助手"
    @click="store.toggleChat()"
  >
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
    </svg>
    <span class="sg-entry-text">帮我挑</span>
  </button>
</template>

<style scoped>
.sg-entry {
  position: fixed;
  right: 24px;
  bottom: 120px;
  z-index: 99;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  background: #ffffff;
  color: #ff5000;
  border-radius: 24px;
  box-shadow: 0 4px 16px rgba(255, 80, 0, 0.18), 0 1px 3px rgba(0, 0, 0, 0.06);
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.sg-entry:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 80, 0, 0.25), 0 2px 6px rgba(0, 0, 0, 0.08);
}

.sg-entry.active {
  opacity: 0;
  pointer-events: none;
  transform: translateY(10px);
}
</style>
