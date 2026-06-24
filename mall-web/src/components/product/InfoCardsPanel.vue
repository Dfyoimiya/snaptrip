<script setup lang="ts">
/**
 * InfoCardsPanel — 信息搜索结构化卡片画布
 *
 * 展示：
 *   1. 结论 (conclusion)
 *   2. 主要亮点 (highlights) — emoji + 标题 + 描述卡片，文字放大
 *   3. 值不值得买 (worth_buying) — 按场景，带判断徽章
 *   4. 避坑指南 (pitfalls)
 *   5. 用户评价汇总 (review_summary) — 评分 + 精选评价
 */
import type { InfoCards } from '@/apis/shoppingGuide'

defineProps<{
  cards: InfoCards
}>()

function verdictClass(verdict: string) {
  if (verdict.includes('很值得')) return 'ic-verdict--yes'
  if (verdict.includes('谨慎')) return 'ic-verdict--caution'
  if (verdict.includes('不推荐')) return 'ic-verdict--no'
  return ''
}

function ratingStars(rating: number) {
  return '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating))
}
</script>

<template>
  <div class="info-cards-scroll">
    <!-- ═══ 结论 ═══ -->
    <div class="ic-conclusion-wrap">
      <div class="ic-conclusion-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z" clip-rule="evenodd" />
        </svg>
      </div>
      <p class="ic-conclusion-text">{{ cards.conclusion || '数据不足，暂无结论' }}</p>
    </div>

    <!-- ═══ 主要亮点 ═══ -->
    <div v-if="cards.highlights.length" class="ic-section">
      <h3 class="ic-section-title">主要亮点</h3>
      <div class="ic-highlights-grid">
        <div
          v-for="(h, i) in cards.highlights"
          :key="i"
          class="ic-highlight-card"
        >
          <span class="ic-highlight-emoji">{{ h.emoji || '💡' }}</span>
          <span class="ic-highlight-title">{{ h.title }}</span>
          <span class="ic-highlight-desc">{{ h.description }}</span>
        </div>
      </div>
    </div>
    <div v-else class="ic-section">
      <h3 class="ic-section-title">主要亮点</h3>
      <p class="ic-empty-hint">暂无亮点数据</p>
    </div>

    <!-- ═══ 值不值得买 ═══ -->
    <div v-if="cards.worth_buying.length" class="ic-section">
      <h3 class="ic-section-title">值不值得买？</h3>
      <div class="ic-worth-list">
        <div
          v-for="(w, i) in cards.worth_buying"
          :key="i"
          class="ic-worth-card"
        >
          <div class="ic-worth-top">
            <span class="ic-worth-scenario">{{ i + 1 }}. {{ w.scenario }}</span>
            <span class="ic-worth-verdict" :class="verdictClass(w.verdict)">
              {{ w.verdict }}
            </span>
          </div>
          <p class="ic-worth-reason">{{ w.reasoning }}</p>
        </div>
      </div>
    </div>
    <div v-else class="ic-section">
      <h3 class="ic-section-title">值不值得买？</h3>
      <p class="ic-empty-hint">暂无场景分析</p>
    </div>

    <!-- ═══ 避坑指南 ═══ -->
    <div v-if="cards.pitfalls.length" class="ic-section">
      <h3 class="ic-section-title">避坑指南</h3>
      <div class="ic-pitfalls-list">
        <div
          v-for="(p, i) in cards.pitfalls"
          :key="i"
          class="ic-pitfall-card"
        >
          <span class="ic-pitfall-icon">⚠️</span>
          <div class="ic-pitfall-content">
            <span class="ic-pitfall-title">{{ p.title }}</span>
            <span class="ic-pitfall-desc">{{ p.description }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="ic-section">
      <h3 class="ic-section-title">避坑指南</h3>
      <p class="ic-empty-hint">暂无避坑数据</p>
    </div>

    <!-- ═══ 用户评价 ═══ -->
    <div class="ic-section">
      <h3 class="ic-section-title">用户评价</h3>
      <div v-if="cards.review_summary && cards.review_summary.total_count > 0" class="ic-reviews-wrap">
        <!-- 评分总览 -->
        <div class="ic-review-header">
          <div class="ic-review-score">
            <span class="ic-review-rating">{{ cards.review_summary.average_rating.toFixed(1) }}</span>
            <span class="ic-review-max">/5</span>
          </div>
          <div class="ic-review-stars">{{ ratingStars(cards.review_summary.average_rating) }}</div>
          <span class="ic-review-count">{{ cards.review_summary.total_count }} 条评价</span>
        </div>
        <p v-if="cards.review_summary.summary_text" class="ic-review-summary">
          {{ cards.review_summary.summary_text }}
        </p>
        <!-- 精选评价 -->
        <div v-if="cards.review_summary.top_reviews.length" class="ic-top-reviews">
          <div
            v-for="r in cards.review_summary.top_reviews"
            :key="r.review_id"
            class="ic-review-item"
          >
            <div class="ic-review-item-top">
              <span class="ic-review-user">{{ r.user_name }}</span>
              <span class="ic-review-item-stars">{{ '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating) }}</span>
            </div>
            <p class="ic-review-content">{{ r.content }}</p>
          </div>
        </div>
      </div>
      <div v-else-if="cards.review_summary?.summary_text" class="ic-reviews-wrap">
        <p class="ic-review-summary">{{ cards.review_summary.summary_text }}</p>
      </div>
      <p v-else class="ic-empty-hint">暂无用户评价</p>
    </div>

    <!-- ═══ 底部：来源 + 耗时 ═══ -->
    <div class="ic-footer">
      <span v-if="cards.sources_used?.length">
        数据来源：{{ cards.sources_used.map(s => s === 'web' ? '网络搜索' : '用户评价').join(' + ') }}
      </span>
      <span v-if="cards.total_latency_ms">
        耗时 {{ (cards.total_latency_ms / 1000).toFixed(1) }}s
      </span>
    </div>
  </div>
</template>

<style scoped>
.info-cards-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 100px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── 结论 ── */
.ic-conclusion-wrap {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(255, 80, 0, 0.06), rgba(255, 140, 0, 0.04));
  border: 1px solid rgba(255, 80, 0, 0.15);
  border-radius: 12px;
}

.ic-conclusion-icon {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  color: #ff5000;
  margin-top: 1px;
}

.ic-conclusion-text {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.6;
  color: #1a1a1a;
  margin: 0;
}

/* ── 区块 ── */
.ic-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ic-section-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.ic-empty-hint {
  font-size: 12px;
  color: #bbb;
  margin: 0;
  font-style: italic;
}

/* ── 亮点卡片 ── */
.ic-highlights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.ic-highlight-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 12px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  text-align: center;
  transition: box-shadow 0.15s;
}

.ic-highlight-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.ic-highlight-emoji {
  font-size: 28px;
  line-height: 1;
}

.ic-highlight-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.3;
}

.ic-highlight-desc {
  font-size: 12px;
  color: #888;
  line-height: 1.4;
}

/* ── 值不值得买 ── */
.ic-worth-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ic-worth-card {
  padding: 12px 14px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
}

.ic-worth-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.ic-worth-scenario {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.ic-worth-verdict {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 10px;
  flex-shrink: 0;
}

.ic-verdict--yes {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.ic-verdict--caution {
  background: rgba(251, 191, 36, 0.12);
  color: #ca8a04;
}

.ic-verdict--no {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.ic-worth-reason {
  font-size: 12px;
  color: #888;
  line-height: 1.5;
  margin: 0;
}

/* ── 避坑指南 ── */
.ic-pitfalls-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ic-pitfall-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.1);
  border-radius: 10px;
}

.ic-pitfall-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.ic-pitfall-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ic-pitfall-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.ic-pitfall-desc {
  font-size: 12px;
  color: #888;
  line-height: 1.5;
}

/* ── 用户评价 ── */
.ic-reviews-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ic-review-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ic-review-score {
  display: flex;
  align-items: baseline;
  gap: 1px;
}

.ic-review-rating {
  font-size: 32px;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1;
}

.ic-review-max {
  font-size: 14px;
  color: #999;
  font-weight: 500;
}

.ic-review-stars {
  font-size: 16px;
  color: #f59e0b;
  letter-spacing: 1px;
}

.ic-review-count {
  font-size: 12px;
  color: #999;
}

.ic-review-summary {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  margin: 0;
}

.ic-top-reviews {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ic-review-item {
  padding: 10px 14px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
}

.ic-review-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.ic-review-user {
  font-size: 12px;
  font-weight: 600;
  color: #555;
}

.ic-review-item-stars {
  font-size: 11px;
  color: #f59e0b;
}

.ic-review-content {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  margin: 0;
}

/* ── 底部 ── */
.ic-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 11px;
  color: #bbb;
}
</style>
