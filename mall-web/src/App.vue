<script setup lang="ts">
/**
 * ============================================
 * 应用根组件
 * 全局使用 AppLayout 布局包裹所有页面内容
 * ============================================
 */
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <RouterView />
  </AppLayout>
</template>

<style>
/* 全局样式已在 main.css 中导入 Tailwind */
</style>
