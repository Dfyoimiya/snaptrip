<script setup lang="ts">
/**
 * ============================================
 * 发现好物 — Pinterest 瀑布流发现页
 *
 * 按主题聚合的商品发现 feed，瀑布流卡片展示。
 * 当前使用 mock 数据，后续可接入 AI 生成主题 API。
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ── Mock 主题数据 ──
interface DiscoveryTheme {
  id: number
  title: string
  subtitle: string
  count: number
  gradient: string
  themeColor: string
}

const themes = ref<DiscoveryTheme[]>([
  { id: 1, title: '通勤穿搭灵感', subtitle: '轻商务风格', count: 12, gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', themeColor: '#667eea' },
  { id: 2, title: '治愈系家居好物', subtitle: '温馨小窝必备', count: 8, gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', themeColor: '#f093fb' },
  { id: 3, title: '高效办公利器', subtitle: '生产力UP', count: 15, gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', themeColor: '#4facfe' },
  { id: 4, title: '周末出游装备', subtitle: '说走就走', count: 10, gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', themeColor: '#43e97b' },
  { id: 5, title: '高颜值数码配件', subtitle: '桌面美学', count: 9, gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', themeColor: '#fa709a' },
  { id: 6, title: '厨房里的仪式感', subtitle: '美食家必备', count: 14, gradient: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', themeColor: '#a18cd1' },
  { id: 7, title: '宠物主子专属', subtitle: '毛孩子的最爱', count: 7, gradient: 'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)', themeColor: '#fccb90' },
  { id: 8, title: '运动达人装备库', subtitle: '燃脂进行时', count: 11, gradient: 'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)', themeColor: '#e0c3fc' },
  { id: 9, title: '咖啡爱好者的角落', subtitle: '每日一杯', count: 6, gradient: 'linear-gradient(135deg, #f5a623 0%, #f76b1c 100%)', themeColor: '#f5a623' },
  { id: 10, title: '文具控天堂', subtitle: '记录生活', count: 18, gradient: 'linear-gradient(135deg, #6dd5ed 0%, #2193b0 100%)', themeColor: '#6dd5ed' },
  { id: 11, title: '卧室好眠指南', subtitle: '深度睡眠', count: 8, gradient: 'linear-gradient(135deg, #2b2d42 0%, #8d99ae 100%)', themeColor: '#2b2d42' },
  { id: 12, title: '户外露营清单', subtitle: '亲近自然', count: 13, gradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)', themeColor: '#11998e' },
  { id: 13, title: '简约收纳灵感', subtitle: '空间翻倍', count: 9, gradient: 'linear-gradient(135deg, #d4a5a5 0%, #7c6f8c 100%)', themeColor: '#d4a5a5' },
  { id: 14, title: '植物美学生活', subtitle: '绿意盎然', count: 5, gradient: 'linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)', themeColor: '#56ab2f' },
  { id: 15, title: '送礼灵感集', subtitle: '心意之选', count: 16, gradient: 'linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%)', themeColor: '#fc4a1a' },
  { id: 16, title: '极简主义好物', subtitle: '少即是多', count: 7, gradient: 'linear-gradient(135deg, #c2c2c2 0%, #e6e6e6 100%)', themeColor: '#c2c2c2' },
])

// ── 主题筛选 ──
const filterOptions = ['全部主题', '穿搭', '家居', '数码', '运动', '美食', '办公', '户外', '生活']
const activeFilter = ref('全部主题')

const filteredThemes = computed(() => {
  if (activeFilter.value === '全部主题') return themes.value
  return themes.value.filter(t => {
    const categoryMap: Record<string, string[]> = {
      '穿搭': ['穿搭', '饰品', '配件'],
      '家居': ['家居', '卧室', '收纳', '厨房'],
      '数码': ['数码', '办公', '文具'],
      '运动': ['运动', '户外', '露营'],
      '美食': ['美食', '咖啡'],
      '办公': ['办公', '文具', '收纳'],
      '户外': ['户外', '露营', '出游', '运动'],
      '生活': ['生活', '宠物', '植物', '极简', '送礼'],
    }
    const keywords = categoryMap[activeFilter.value] || []
    return keywords.some(kw =>
      t.title.includes(kw) || t.subtitle.includes(kw),
    )
  })
})

function handleCardClick(theme: DiscoveryTheme) {
  router.push({ path: '/search', query: { theme: theme.title } })
}

function handleFilterChange(filter: string) {
  activeFilter.value = filter
}

/** 随机调整卡片图片区域高度，模拟不同尺寸图片的瀑布流效果 */
const cardHeights = [160, 200, 240, 180, 220, 190]
function getCardHeight(index: number): string {
  return `${cardHeights[index % cardHeights.length]}px`
}
</script>

<template>
  <div class="discover-page">
    <!-- ── 页头 ── -->
    <div class="discover-header">
      <div class="discover-header-left">
        <h1 class="discover-title">发现好物</h1>
        <p class="discover-subtitle">探索精选主题，发现属于你的好物灵感</p>
      </div>
      <div class="discover-filter">
        <span class="discover-filter-label">主题筛选</span>
        <div class="discover-filter-select-wrap">
          <select
            v-model="activeFilter"
            class="discover-filter-select"
            @change="handleFilterChange(activeFilter)"
          >
            <option v-for="opt in filterOptions" :key="opt" :value="opt">
              {{ opt }}
            </option>
          </select>
          <svg xmlns="http://www.w3.org/2000/svg" class="discover-filter-arrow" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </div>
    </div>

    <!-- ── 无结果 ── -->
    <div v-if="!filteredThemes.length" class="discover-empty">
      <div class="discover-empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
      </div>
      <p class="discover-empty-text">暂无「{{ activeFilter }}」相关主题</p>
      <button class="discover-empty-btn" @click="activeFilter = '全部主题'">查看全部主题</button>
    </div>

    <!-- ── 瀑布流网格 ── -->
    <div v-else class="masonry">
      <div
        v-for="(theme, index) in filteredThemes"
        :key="theme.id"
        class="masonry-item"
      >
        <button class="discover-card" @click="handleCardClick(theme)">
          <!-- 图片 / 渐变占位 -->
          <div
            class="discover-card-img"
            :style="{
              background: theme.gradient,
              height: getCardHeight(index),
            }"
          >
            <div class="discover-card-img-overlay">
              <span class="discover-card-theme-badge">{{ theme.subtitle }}</span>
            </div>
          </div>

          <!-- 卡片信息 -->
          <div class="discover-card-body">
            <h3 class="discover-card-title">{{ theme.title }}</h3>
            <span class="discover-card-count">{{ theme.count }} 件好物</span>
          </div>
        </button>
      </div>
    </div>

    <!-- ── 底部加载更多提示 ── -->
    <div class="discover-more">
      <p class="discover-more-text">下拉加载更多 · AI 持续为你生成主题灵感</p>
    </div>
  </div>
</template>

<style scoped>
.discover-page {
  width: 100%;
}

/* ── 页头 ── */
.discover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 16px;
}

.discover-header-left {
  flex: 1;
  min-width: 0;
}

.discover-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.discover-subtitle {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* ── 筛选 ── */
.discover-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.discover-filter-label {
  font-size: 13px;
  color: #888;
  white-space: nowrap;
}

.discover-filter-select-wrap {
  position: relative;
}

.discover-filter-select {
  appearance: none;
  padding: 7px 36px 7px 14px;
  font-size: 13px;
  color: #333;
  background: #f5f5f5;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  cursor: pointer;
  outline: none;
  transition: all 0.15s;
}

.discover-filter-select:hover {
  border-color: #ccc;
}

.discover-filter-select:focus {
  border-color: #ff5000;
  box-shadow: 0 0 0 2px rgba(255, 80, 0, 0.1);
}

.discover-filter-arrow {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  color: #999;
  pointer-events: none;
}

/* ── 空状态 ── */
.discover-empty {
  text-align: center;
  padding: 80px 20px;
}

.discover-empty-icon {
  display: inline-flex;
  color: #ddd;
  margin-bottom: 16px;
}

.discover-empty-text {
  font-size: 14px;
  color: #999;
  margin: 0 0 16px;
}

.discover-empty-btn {
  padding: 8px 24px;
  font-size: 13px;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.06);
  border: 1px solid rgba(255, 80, 0, 0.2);
  border-radius: 8px;
  transition: all 0.15s;
}

.discover-empty-btn:hover {
  background: rgba(255, 80, 0, 0.12);
}

/* ── 瀑布流 ── */
.masonry {
  column-count: 4;
  column-gap: 16px;
}

.masonry-item {
  break-inside: avoid;
  margin-bottom: 16px;
}

/* ── 卡片 ── */
.discover-card {
  display: block;
  width: 100%;
  text-align: left;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
  cursor: pointer;
}

.discover-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
  border-color: #e0e0e0;
}

/* ── 卡片图片区域 ── */
.discover-card-img {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.discover-card-img-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    to bottom,
    transparent 40%,
    rgba(0, 0, 0, 0.3) 100%
  );
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 12px;
}

.discover-card-theme-badge {
  font-size: 11px;
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 3px 10px;
  border-radius: 20px;
  font-weight: 500;
  letter-spacing: 0.3px;
}

/* ── 卡片信息 ── */
.discover-card-body {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.discover-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.discover-card-count {
  font-size: 12px;
  color: #ff5000;
  background: rgba(255, 80, 0, 0.06);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── 底部提示 ── */
.discover-more {
  text-align: center;
  padding: 40px 0 20px;
}

.discover-more-text {
  font-size: 13px;
  color: #ccc;
  margin: 0;
}

/* ── 响应式 ── */
@media (max-width: 639px) {
  .masonry {
    column-count: 2;
    column-gap: 12px;
  }
  .masonry-item {
    margin-bottom: 12px;
  }
  .discover-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (min-width: 640px) and (max-width: 1023px) {
  .masonry {
    column-count: 3;
  }
}

@media (min-width: 1200px) {
  .masonry {
    column-count: 4;
  }
}

@media (min-width: 1536px) {
  .masonry {
    column-count: 5;
  }
}
</style>
