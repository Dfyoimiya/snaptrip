<script setup lang="ts">
/**
 * ============================================
 * 全局布局 — 三层架构
 *
 * 底层：灰白底色 (#f5f5f5)，商品/文字直接平铺
 * 中层：RouterView 子页面内容，自然滚动
 * 顶层：TopBar / LeftSidebar
 *      TopBar 和侧边栏固定，搜索框随页面自然滚动
 * ============================================
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useMemberStore } from '@/stores/member'
import { useCartStore } from '@/stores/cart'
import TopBar from './TopBar.vue'
import HeaderSearch from './HeaderSearch.vue'
import LeftSidebar from './LeftSidebar.vue'
import ProductCompare from '@/components/product/ProductCompare.vue'

const router = useRouter()
const route = useRoute()
const layoutStore = useLayoutStore()
const memberStore = useMemberStore()
const cartStore = useCartStore()

layoutStore.applyTheme()

const userName = computed(() => memberStore.displayName || '用户')
const fillMain = computed(() => route.meta.fillMain === true)

function navigateTo(path: string) {
  router.push(path)
}

function handleLogout() {
  memberStore.memberLogout()
  cartStore.clearCart()
  router.push('/')
}
</script>

<template>
  <div class="app-layout">
    <!-- ═══ 顶层：悬浮组件，fixed 定位 ═══ -->
    <div class="top-bar-fixed">
      <TopBar
        :is-logged-in="memberStore.isLoggedIn"
        :display-name="userName"
        :cart-count="cartStore.totalCount"
        @navigate="navigateTo"
        @logout="handleLogout"
      />
    </div>
    <LeftSidebar />
    <!-- 搜索框位于页面顶部，向下滚动时自然离开视口，回到顶部时显示 -->
    <HeaderSearch mode="inline" @navigate="navigateTo" />

    <!-- ═══ 中层：子页面内容 ═══ -->
    <main class="main-content" :class="{ 'main-content--fill': fillMain }">
      <div class="route-content">
        <slot />
      </div>
    </main>

    <!-- ═══ 商品对比浮层 ═══ -->
    <Teleport to="body">
      <div v-if="layoutStore.isComparing" class="compare-overlay" @click.self="layoutStore.endCompare()">
        <div class="compare-modal">
          <ProductCompare
            :products="layoutStore.compareProducts"
            @close="layoutStore.endCompare()"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   底层：灰白纸
   ═══════════════════════════════════════════ */
.app-layout {
  min-height: 100vh;
  color: var(--mall-text);
  background: var(--mall-page-bg);
  transition: color 0.2s ease, background-color 0.2s ease;
}

/* ═══════════════════════════════════════════
   TopBar 顶部通栏
   ═══════════════════════════════════════════ */
.top-bar-fixed {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 60;
  height: 36px;
}

/* ═══════════════════════════════════════════
   中层：内容区
   侧边栏 184px + 左侧偏移 12px + 间距 12px = 208px
   ═══════════════════════════════════════════ */
.main-content {
  padding: 16px 19px 0 208px;
}

.route-content {
  width: 100%;
}

.main-content--fill {
  min-height: calc(100vh - 12px);
}

.main-content--fill .route-content {
  min-height: calc(100vh - 128px);
}

@media (max-width: 1023px) {
  .main-content {
    padding-left: 19px;
  }
}

/* ═══════════════════════════════════════════
   对比浮层
   ═══════════════════════════════════════════ */
.compare-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.compare-modal {
  width: 100%;
  max-width: 960px;
  max-height: 85vh;
  overflow-y: auto;
  border-radius: 16px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.2);
}
</style>
