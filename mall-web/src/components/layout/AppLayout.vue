<script setup lang="ts">
/**
 * ============================================
 * 全局布局 — 三层架构
 *
 * 底层：灰白底色 (#f5f5f5)，商品/文字直接平铺
 * 中层：RouterView 子页面内容，自然滚动
 * 顶层：LeftSidebar / HeaderSearch / TabBar
 *      各组件独立 fixed 定位 + 液态玻璃风格
 * ============================================
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import TabBar from './TabBar.vue'
import HeaderSearch from './HeaderSearch.vue'
import LeftSidebar from './LeftSidebar.vue'
import ProductCompare from '@/components/product/ProductCompare.vue'

const router = useRouter()
const layoutStore = useLayoutStore()

const contentPaddingLeft = computed(() => {
  const w = layoutStore.leftSidebarExpanded || layoutStore.leftSidebarLocked ? 200 : 64
  return `${w + 12 + 20}px`
})

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="app-layout">
    <!-- ═══ 顶层：悬浮组件，fixed 定位 ═══ -->
    <LeftSidebar />
    <HeaderSearch mode="inline" @navigate="navigateTo" />
    <TabBar />

    <!-- ═══ 中层：子页面内容 ═══ -->
    <main class="main-content" :style="{ paddingLeft: contentPaddingLeft }">
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
   中层：内容区
   padding 避让顶层 fixed 组件
   ═══════════════════════════════════════════ */
.main-content {
  padding: 106px 19px 0 96px;
  transition: padding-left 0.2s ease;
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
