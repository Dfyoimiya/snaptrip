<script setup lang="ts">
/**
 * ============================================
 * 全局布局 — 三层架构
 *
 * 底层：灰白底色 (#f5f5f5)，商品/文字直接平铺
 * 中层：RouterView 子页面内容，自然滚动
 * 顶层：TopBar / LeftSidebar / HeaderSearch / TabBar
 *      各组件独立 fixed 定位 + 液态玻璃风格
 * ============================================
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useMemberStore } from '@/stores/member'
import { useCartStore } from '@/stores/cart'
import TopBar from './TopBar.vue'
import TabBar from './TabBar.vue'
import HeaderSearch from './HeaderSearch.vue'
import LeftSidebar from './LeftSidebar.vue'
import ProductCompare from '@/components/product/ProductCompare.vue'

const router = useRouter()
const layoutStore = useLayoutStore()
const memberStore = useMemberStore()
const cartStore = useCartStore()

const userName = computed(() => {
  const info = memberStore.userInfo
  return (info as any)?.nickname || (info as any)?.username || '用户'
})

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
    <HeaderSearch mode="inline" @navigate="navigateTo" />
    <TabBar />

    <!-- ═══ 中层：子页面内容 ═══ -->
    <main class="main-content">
      <slot />
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
  background: #f5f5f5;
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
   侧边栏 200px + 左侧偏移 12px + 间距 20px = 232px
   ═══════════════════════════════════════════ */
.main-content {
  padding: 116px 19px 0 232px;
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
