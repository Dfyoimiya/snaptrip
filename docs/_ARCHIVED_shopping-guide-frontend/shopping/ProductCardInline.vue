<script setup lang="ts">
/**
 * ============================================
 * 内联商品卡片 — 对话流中嵌入的可点击商品卡片
 *
 * 展示商品名、价格、购买链接
 * 暖色调匹配导购面板风格
 * ============================================
 */

import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps<{
  name: string
  productId: string
  url: string
  price?: number
  image?: string
}>()

function handleClick(e: Event) {
  e.preventDefault()
  if (props.url.startsWith('/')) {
    router.push(props.url)
  } else {
    window.open(props.url, '_blank', 'noopener')
  }
}
</script>

<template>
  <a
    :href="url"
    class="product-card-inline"
    @click="handleClick"
  >
    <div class="card-img" v-if="image">
      <img :src="image" :alt="name" />
    </div>
    <div class="card-body">
      <h4 class="card-name">{{ name }}</h4>
      <div class="card-price-row" v-if="price">
        <span class="card-price">¥{{ price.toFixed(2) }}</span>
      </div>
      <div class="card-action">
        <span>查看详情</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="card-arrow">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </div>
    </div>
  </a>
</template>

<style scoped>
.product-card-inline {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e0d8ce;
  border-radius: 12px;
  background: #f5f0eb;
  transition: all 0.15s;
  text-decoration: none;
  color: inherit;
}

.product-card-inline:hover {
  border-color: #b85c3a;
  background: #ede4dc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-img {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: #e8e3dc;
}

.card-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-name {
  font-size: 14px;
  font-weight: 500;
  color: #2d2a26;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-price-row {
  margin-top: 4px;
}

.card-price {
  font-size: 16px;
  font-weight: 700;
  color: #b85c3a;
}

.card-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #b85c3a;
  font-weight: 500;
  margin-top: 4px;
}

.card-arrow {
  width: 14px;
  height: 14px;
  transition: transform 0.15s;
}

.product-card-inline:hover .card-arrow {
  transform: translateX(3px);
}
</style>
