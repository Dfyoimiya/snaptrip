<script setup lang="ts">
/**
 * ============================================
 * 支付成功页 (PaySuccessView)
 * 对应原项目 pages/money/paySuccess.vue
 * PC端适配：居中展示 + 操作按钮
 * ============================================
 */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAlipayStatusAPI } from '@/apis/order'

const route = useRoute()
const router = useRouter()

/** 支付状态文字 */
const payText = ref('支付成功')
/** 是否加载中 */
const loading = ref(false)

/** 查询支付宝交易状态 */
const loadData = async (outTradeNo: string) => {
  loading.value = true
  try {
    const res = await fetchAlipayStatusAPI(outTradeNo)
    const tradeStatus = res.data
    if (tradeStatus != null && tradeStatus === 'TRADE_SUCCESS') {
      payText.value = '支付成功'
    } else {
      payText.value = '支付失败'
    }
  } catch (e) {
    console.error('查询支付宝状态失败', e)
    payText.value = '支付失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const outTradeNo = route.query.out_trade_no as string
  if (outTradeNo) {
    loadData(outTradeNo)
  }
})
</script>

<template>
  <div class="min-h-[600px] flex items-center justify-center bg-gray-50">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-16 max-w-lg w-full mx-4 text-center">
      <!-- 状态图标 -->
      <div class="mb-6">
        <div v-if="payText === '支付成功'" class="w-24 h-24 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div v-else class="w-24 h-24 rounded-full bg-red-100 flex items-center justify-center mx-auto">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      </div>

      <!-- 状态文字 -->
      <h1 class="text-2xl font-bold text-gray-900 mb-2">{{ payText }}</h1>
      <p class="text-gray-400 text-sm mb-10">
        {{ payText === '支付成功' ? '感谢您的购买，我们将尽快为您发货' : '支付过程中出现问题，请重新尝试' }}
      </p>

      <!-- 操作按钮 -->
      <div class="flex gap-4 justify-center">
        <button
          class="px-8 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
          @click="router.push('/member/orders')"
        >
          查看订单
        </button>
        <button
          class="px-8 py-3 border border-gray-200 text-gray-700 rounded-lg font-medium hover:border-red-300 hover:text-red-600 transition-colors"
          @click="router.push('/')"
        >
          返回首页
        </button>
      </div>
    </div>
  </div>
</template>
