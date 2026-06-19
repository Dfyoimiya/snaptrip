<script lang="ts" setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useTabStore } from '@/stores/tab'
import type { TabView } from '@/stores/tab'
import Navbar from './components/Navbar.vue'
import Sidebar from './components/Sidebar/index.vue'
import AppMain from './components/AppMain.vue'
import AssistantPanel from '@/views/ai/AssistantPanel.vue'
import useResizeHandler from './composables/useResizeHandler'

const appStore = useAppStore()
const tabStore = useTabStore()
const route = useRoute()

const sidebar = computed(() => appStore.sidebar)
const device = computed(() => appStore.device)

const classObj = computed(() => ({
  hideSidebar: !sidebar.value.opened,
  withoutAnimation: sidebar.value.withoutAnimation,
  mobile: device.value === 'mobile',
}))

// 路由变化时自动添加 Tab
watch(
  () => route.path,
  () => {
    if (route.path.startsWith('/redirect')) return
    tabStore.addView({
      name: route.name as string,
      path: route.path,
      fullPath: route.fullPath,
      meta: route.meta as Record<string, any>,
      title: route.meta?.title as string,
    })
  },
  { immediate: true }
)

useResizeHandler()
</script>

<template>
  <div class="app-wrapper" :class="classObj">
    <Sidebar class="sidebar-container" />
    <div
      v-if="device === 'mobile' && sidebar.opened"
      class="mobile-mask"
      @click="appStore.closeSidebar(false)"
    />
    <div class="main-container">
      <Navbar class="fixed-header" />
      <AppMain />
    </div>
    <AssistantPanel />
  </div>
</template>

<style lang="scss" scoped>
.app-wrapper {
  position: relative;
  height: 100vh;
  width: 100%;
  display: flex;

  .sidebar-container {
    width: 240px;
    min-width: 240px;
    max-width: 240px;
    height: 100%;
    transition: width 0.25s ease, min-width 0.25s ease, max-width 0.25s ease;
    flex-shrink: 0;
  }

  .main-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    background-color: var(--admin-bg);
    overflow: hidden;

    .fixed-header {
      flex-shrink: 0;
      z-index: 100;
    }
  }

  // 收起
  &.hideSidebar {
    .sidebar-container {
      width: 0;
      min-width: 0;
      max-width: 0;
      border: 0;
      box-shadow: none;
    }
  }

  // 移动端
  &.mobile {
    .sidebar-container {
      position: fixed;
      top: 0;
      left: 0;
      z-index: 999;
      height: 100%;
      width: 240px;
      min-width: 240px;
      max-width: 240px;
      transition: transform 0.25s ease;
      box-shadow: 12px 0 32px rgba(15, 23, 42, 0.18);
    }

    &.hideSidebar .sidebar-container {
      transform: translateX(-100%);
      pointer-events: none;
    }
  }

  .mobile-mask {
    position: fixed;
    inset: 0;
    z-index: 998;
    background: rgba(15, 23, 42, 0.42);
    backdrop-filter: blur(2px);
  }
}
</style>
