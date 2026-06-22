<script setup lang="ts">
/**
 * ============================================
 * 商品对比组件 — 多列对比表格 + AI 分析
 *
 * Props:
 *   products: ProductSummary[] (2-5 件商品)
 *
 * Emits:
 *   close — 关闭对比视图
 * ============================================
 */
import { ref, computed } from 'vue'
import type { ProductSummary } from '@/types'

// ── Props & Emits ──
const props = defineProps<{
  products: ProductSummary[]
}>()

defineEmits<{
  close: []
}>()

// ── AI 分析状态 ──
const aiLoading = ref(false)
const aiSummary = ref('')
const aiExpanded = ref(false)

async function handleAiAnalysis() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiSummary.value = ''

  // 模拟 AI 分析延迟
  await new Promise(resolve => setTimeout(resolve, 2000))

  const names = props.products.map(p => p.name).join('、')
  aiSummary.value = `综合对比 ${names}，以下是我的分析建议：

1. **性价比**：${props.products[0]?.name || '未知'} 的价格（¥${(props.products[0]?.price || 0).toLocaleString('zh-CN')}）在同类中较为优惠，综合配置看性价比较高。
2. **品牌口碑**：${props.products.find(p => p.brand)?.brand || '未知品牌'} 品牌在用户口碑中评分较高，售后服务质量稳定。
3. **选购建议**：如果预算有限，推荐 ${props.products[0]?.name || '商品A'}；如果追求品牌和品质，建议选择有品牌背书的商品。

以上为初步分析，具体商品参数请以详情页为准。更多细节，可以点击商品查看完整信息。`
  aiLoading.value = false
  aiExpanded.value = true
}

// ── 派生数据 ──

const cols = computed(() => props.products.length)

/** 价格最低的那个 */
const minPriceId = computed(() => {
  if (props.products.length < 2) return null
  const first = props.products[0]
  if (!first) return null
  return props.products.reduce((min, p) => (p.price < min.price ? p : min), first).id
})

// ── 工具函数 ──
function formatPrice(p: number): string {
  return p.toLocaleString('zh-CN')
}

function isLowestPrice(id: string | number): boolean {
  return id === minPriceId.value
}
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
    <!-- ── Header ── -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
      <h2 class="text-lg font-bold text-gray-800">商品对比</h2>
      <div class="flex items-center gap-3">
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
          :class="
            aiLoading
              ? 'bg-purple-50 text-purple-400 cursor-wait'
              : aiSummary
                ? 'bg-purple-50 text-purple-600 hover:bg-purple-100'
                : 'bg-brand-50 text-brand-600 hover:bg-brand-100'
          "
          :disabled="aiLoading"
          @click="handleAiAnalysis"
        >
          <!-- loading spinner -->
          <span
            v-if="aiLoading"
            class="inline-block w-3.5 h-3.5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin"
          />
          <span v-else class="text-base leading-none">&#x2728;</span>
          {{ aiLoading ? '分析中...' : 'AI 帮我分析' }}
        </button>
        <button
          class="text-gray-400 hover:text-gray-600 transition-colors text-lg leading-none p-1"
          title="关闭对比"
          @click="$emit('close')"
        >
          &times;
        </button>
      </div>
    </div>

    <!-- ── 对比表格 ── -->
    <div
      class="overflow-x-auto"
      :class="{ 'pb-4': cols >= 4 }"
    >
      <table class="w-full min-w-[600px]">
        <colgroup>
          <col style="width: 120px" />
          <col v-for="i in cols" :key="'col-' + i" style="min-width: 180px" />
        </colgroup>

        <!-- 图片行 -->
        <tr>
          <td class="text-sm text-gray-500 font-medium pl-6 py-4 align-top bg-gray-50/30">商品图片</td>
          <td
            v-for="product in products"
            :key="'img-' + product.id"
            class="px-4 py-4 align-top text-center"
          >
            <div class="w-40 h-40 mx-auto rounded-xl bg-gray-100 overflow-hidden">
              <img
                v-if="product.image"
                :src="product.image"
                :alt="product.name"
                class="w-full h-full object-cover"
              />
              <div
                v-else
                class="w-full h-full flex items-center justify-center text-gray-300 text-sm"
              >
                暂无图片
              </div>
            </div>
          </td>
        </tr>

        <!-- 名称行 -->
        <tr class="border-t border-gray-50">
          <td class="text-sm text-gray-500 font-medium pl-6 py-3 bg-gray-50/30">商品名称</td>
          <td
            v-for="product in products"
            :key="'name-' + product.id"
            class="px-4 py-3 text-sm text-gray-800 font-medium text-center"
          >
            {{ product.name }}
          </td>
        </tr>

        <!-- 价格行 -->
        <tr class="border-t border-gray-50">
          <td class="text-sm text-gray-500 font-medium pl-6 py-3 bg-gray-50/30">价格</td>
          <td
            v-for="product in products"
            :key="'price-' + product.id"
            class="px-4 py-3 text-center"
          >
            <span
              class="text-lg font-bold"
              :class="isLowestPrice(product.id) ? 'text-green-600' : 'text-brand-600'"
            >
              <span class="text-xs">&yen;</span>{{ formatPrice(product.price) }}
            </span>
            <span
              v-if="isLowestPrice(product.id) && cols >= 2"
              class="ml-1.5 text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded"
            >
              最低价
            </span>
          </td>
        </tr>

        <!-- 品牌行 -->
        <tr class="border-t border-gray-50">
          <td class="text-sm text-gray-500 font-medium pl-6 py-3 bg-gray-50/30">品牌</td>
          <td
            v-for="product in products"
            :key="'brand-' + product.id"
            class="px-4 py-3 text-sm text-gray-600 text-center"
          >
            {{ product.brand || '--' }}
          </td>
        </tr>

        <!-- 空状态：如果 products 为空 -->
        <tr v-if="products.length === 0">
          <td colspan="7" class="text-center py-12 text-text-muted text-sm">
            暂无商品需要对比
          </td>
        </tr>
      </table>
    </div>

    <!-- ── AI 总结建议 ── -->
    <div
      v-if="aiSummary || aiLoading"
      class="border-t border-gray-100"
    >
      <!-- 折叠开关 -->
      <button
        class="w-full flex items-center justify-between px-6 py-3 hover:bg-gray-50 transition-colors"
        @click="aiExpanded = !aiExpanded"
      >
        <span class="text-sm font-semibold text-gray-700">
          &#x2728; AI 总结建议
        </span>
        <span
          class="text-gray-400 text-sm transition-transform duration-200"
          :class="{ 'rotate-180': !aiExpanded }"
        >
          &#x25B2;
        </span>
      </button>

      <!-- 内容 -->
      <div
        v-if="aiExpanded"
        class="px-6 pb-5"
      >
        <div
          v-if="aiLoading"
          class="flex items-center gap-3 text-sm text-text-muted py-4"
        >
          <span class="inline-block w-4 h-4 border-2 border-purple-200 border-t-purple-500 rounded-full animate-spin" />
          正在分析商品信息，请稍候...
        </div>
        <div
          v-else
          class="prose prose-sm max-w-none text-gray-700 bg-purple-50/50 rounded-xl p-4"
        >
          <p
            v-for="(line, idx) in aiSummary.split('\n').filter(Boolean)"
            :key="'ai-line-' + idx"
            class="mb-1 last:mb-0"
            v-html="
              line
                .replace(/\*\*(.+?)\*\*/g, '<strong class=\'text-gray-900\'>$1</strong>')
                .trim() || '&nbsp;'
            "
          />
        </div>
      </div>
    </div>
  </div>
</template>
