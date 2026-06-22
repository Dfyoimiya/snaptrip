<script setup lang="ts">
/**
 * ============================================
 * 评价表单弹窗 — 写商品评价
 * ============================================
 */
import { ref, watch } from 'vue'
import { createReviewAPI, type ReviewCreateParams } from '@/apis/review'

// ── Props ──

const props = defineProps<{
  productId: string
  orderId?: string
  visible: boolean
}>()

// ── Emits ──

const emit = defineEmits<{
  'update:visible': [value: boolean]
  submitted: []
}>()

// ── 表单状态 ──

const rating = ref(0)
const hoverRating = ref(0)
const content = ref('')
const isAnonymous = ref(false)
const submitting = ref(false)
const error = ref('')
const success = ref(false)

// ── 交互方法 ──

function setRating(value: number) {
  rating.value = value
  if (error.value) error.value = ''
}

function close() {
  emit('update:visible', false)
}

/** 重置表单 */
watch(() => props.visible, (val) => {
  if (val) {
    rating.value = 0
    hoverRating.value = 0
    content.value = ''
    isAnonymous.value = false
    submitting.value = false
    error.value = ''
    success.value = false
  }
})

/** 提交评价 */
async function handleSubmit() {
  // 验证
  if (rating.value < 1 || rating.value > 5) {
    error.value = '请选择评分'
    return
  }
  if (!content.value || content.value.trim().length < 5) {
    error.value = '请输入至少5个字的评价内容'
    return
  }

  error.value = ''
  submitting.value = true

  try {
    const params: ReviewCreateParams = {
      product_id: props.productId,
      rating: rating.value,
      content: content.value.trim(),
      is_anonymous: isAnonymous.value,
    }
    if (props.orderId) {
      params.order_id = props.orderId
    }

    await createReviewAPI(params)

    // 成功提示
    success.value = true
    emit('submitted')

    // 1.5 秒后自动关闭
    setTimeout(() => {
      close()
    }, 1500)
  } catch (err: any) {
    error.value = err?.message || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩层 -->
    <transition name="modal-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm"
        @click.self="close"
      >
        <!-- 弹窗卡片 -->
        <div class="bg-white w-full max-w-md mx-4 rounded-2xl shadow-2xl overflow-hidden"
          @click.stop
        >
          <!-- 头部 -->
          <div class="flex items-center justify-between px-6 pt-5 pb-3">
            <h2 class="text-lg font-bold text-gray-900">写评价</h2>
            <button
              class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              :disabled="submitting"
              @click="close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 成功状态 -->
          <div v-if="success" class="px-6 pb-6">
            <div class="flex flex-col items-center justify-center py-8 text-center">
              <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p class="text-gray-900 font-medium text-base">评价提交成功！</p>
              <p class="text-gray-400 text-sm mt-1">感谢你的分享</p>
            </div>
          </div>

          <!-- 表单 -->
          <div v-else class="px-6 pb-6 space-y-5">
            <!-- 错误提示 -->
            <div v-if="error" class="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">
              {{ error }}
            </div>

            <!-- 星级评分 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">评分</label>
              <div class="flex items-center gap-1.5">
                <button
                  v-for="star in 5"
                  :key="star"
                  type="button"
                  class="transition-transform hover:scale-110 focus:outline-none"
                  @click="setRating(star)"
                  @mouseenter="hoverRating = star"
                  @mouseleave="hoverRating = 0"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    :class="[
                      'w-8 h-8 cursor-pointer transition-colors',
                      (hoverRating || rating) >= star ? 'text-amber-400' : 'text-gray-200',
                    ]"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                </button>
                <span class="text-sm text-gray-400 ml-2">{{ rating > 0 ? `${rating} 分` : '点击评分' }}</span>
              </div>
            </div>

            <!-- 评价内容 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">评价内容</label>
              <textarea
                v-model="content"
                rows="4"
                maxlength="500"
                placeholder="分享你的使用体验..."
                class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 transition-colors"
              />
              <div class="flex justify-between mt-1">
                <span v-if="content.length > 0 && content.length < 5" class="text-xs text-red-400">至少5个字</span>
                <span v-else class="text-xs text-transparent">-</span>
                <span class="text-xs text-gray-400">{{ content.length }}/500</span>
              </div>
            </div>

            <!-- 匿名评价 -->
            <label class="flex items-center gap-2.5 cursor-pointer select-none">
              <div
                :class="[
                  'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors flex-shrink-0',
                  isAnonymous ? 'bg-brand-600 border-brand-600' : 'border-gray-300 bg-white',
                ]"
                @click="isAnonymous = !isAnonymous"
              >
                <svg v-if="isAnonymous" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <span class="text-sm text-gray-600">匿名评价</span>
            </label>

            <!-- 提交按钮 -->
            <button
              :disabled="submitting"
              class="w-full h-11 bg-brand-600 text-white font-medium text-sm rounded-lg hover:bg-brand-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              @click="handleSubmit"
            >
              <svg
                v-if="submitting"
                class="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              {{ submitting ? '提交中...' : '提交评价' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
