<script lang="ts" setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const routerKey = computed(() => route.path)
</script>

<template>
  <section class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="fade-transform" mode="out-in">
        <keep-alive>
          <component :is="Component" :key="routerKey" />
        </keep-alive>
      </transition>
    </router-view>
  </section>
</template>

<style lang="scss" scoped>
.app-main {
  flex: 1;
  padding: 16px;
  overflow-x: hidden;
  overflow-y: auto;
  background-color: var(--admin-page-bg);
}

/* 页面切换动画 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.2s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(8px);
}
</style>
