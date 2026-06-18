<script setup lang="ts">
/**
 * ============================================
 * 导购助手触发按钮 — 右侧边缘竖条
 *
 * 暖木色调，与面板协调
 * 面板展开时随商品页左移至面板边缘
 * ============================================
 */

import { useShoppingGuideStore } from '@/stores/shoppingGuide'

const guideStore = useShoppingGuideStore()
</script>

<template>
  <button
    class="guide-trigger"
    :class="{ 'guide-trigger--active': guideStore.isOpen }"
    @click="guideStore.togglePanel()"
    :title="guideStore.isOpen ? '收起导购助手' : '打开导购助手 (Ctrl+G)'"
  >
    <span class="trigger-text">
      {{ guideStore.isOpen ? '收起' : '导购助手' }}
    </span>
    <svg
      class="trigger-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        v-if="guideStore.isOpen"
        d="M15 18l-6-6 6-6"
      />
      <template v-else>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="10" r="1" fill="currentColor" stroke="none"/>
        <circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/>
        <circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/>
      </template>
    </svg>
  </button>
</template>

<style scoped>
.guide-trigger {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 42;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: #f5f0ea;
  border: 1px solid #ddd2c4;
  border-right: none;
  border-radius: 10px 0 0 10px;
  box-shadow: -1px 0 8px rgba(80, 50, 30, 0.05);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.guide-trigger:hover {
  background: #e8ddd0;
  border-color: #c4b0a0;
  box-shadow: -2px 0 12px rgba(120, 70, 30, 0.1);
}

.guide-trigger--active {
  right: min(35vw, 480px);
  background: #ede4da;
  border-color: #c4b0a0;
}

.trigger-text {
  font-size: 13px;
  font-weight: 500;
  color: #5d4e3a;
  letter-spacing: 2px;
}

.guide-trigger:hover .trigger-text,
.guide-trigger--active .trigger-text {
  color: #8a5f3c;
}

.trigger-icon {
  width: 18px;
  height: 18px;
  color: #a09080;
}

.guide-trigger:hover .trigger-icon,
.guide-trigger--active .trigger-icon {
  color: #8a5f3c;
}
</style>
