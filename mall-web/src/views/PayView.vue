<script setup lang="ts">
/**
 * ============================================
 * 支付收银台 (PayView)
 * ============================================
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { payOrderAPI } from '@/apis/order'

const route = useRoute()
const router = useRouter()

const orderId = (route.query.orderId as string) || ''
const orderAmount = Number(route.query.amount) || 0

const countdownSeconds = ref(30 * 60)
const paying = ref(false)
const paySuccess = ref(false)
const payError = ref('')

const selectedPayMethod = ref('alipay')
const payMethods = [
  { key: 'alipay', label: '支付宝', desc: '数亿用户的选择，安全快捷', iconBg: 'bg-blue-500', iconChar: '支' },
  { key: 'wechat', label: '微信支付', desc: '微信扫一扫，快速完成支付', iconBg: 'bg-green-500', iconChar: '微' },
  { key: 'card', label: '银行卡支付', desc: '支持各大银行储蓄卡和信用卡', iconBg: 'bg-indigo-500', iconChar: '卡' },
]

const formattedCountdown = computed(() => {
  const m = Math.floor(countdownSeconds.value / 60)
  const s = countdownSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const isExpired = computed(() => countdownSeconds.value <= 0)

let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (!orderId) {
    payError.value = '订单信息缺失，无法支付'
    return
  }
  timer = setInterval(() => {
    if (countdownSeconds.value > 0) {
      countdownSeconds.value--
    } else {
      if (timer) clearInterval(timer)
    }
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const formatPrice = (p: number) => p.toLocaleString('zh-CN', { minimumFractionDigits: 2 })

const handlePay = async () => {
  if (isExpired.value || !orderId) return
  paying.value = true
  payError.value = ''
  try {
    await payOrderAPI(orderId)
    paySuccess.value = true
  } catch (e: any) {
    payError.value = e?.message || '支付失败，请重试'
  } finally {
    paying.value = false
  }
}

const goOrderDetail = () => {
  router.push(`/order/${orderId}`)
}
</script>

<template>
  <div class="pay-page min-h-[50vh] flex flex-col items-center justify-center py-10">
    <!-- 成功状态 -->
    <div v-if="paySuccess" class="text-center space-y-4">
      <div class="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold text-gray-900">支付成功</h2>
      <p class="text-gray-500">您的订单 <span class="font-mono text-gray-700">{{ orderId }}</span> 已支付成功</p>
      <p class="text-2xl font-bold text-red-600">&yen;{{ formatPrice(orderAmount) }}</p>
      <div class="flex items-center gap-3 justify-center pt-4">
        <button class="px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium" @click="goOrderDetail">
          查看订单
        </button>
        <button class="px-6 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors" @click="router.push('/')">
          返回首页
        </button>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="payError && !orderId" class="text-center space-y-4">
      <div class="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mx-auto">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
      <h2 class="text-xl font-bold text-gray-900">无法支付</h2>
      <p class="text-gray-500">{{ payError }}</p>
      <button class="px-6 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50" @click="router.push('/')">
        返回首页
      </button>
    </div>

    <!-- 支付页面 -->
    <div v-else class="w-full max-w-[600px]">
      <div class="text-center mb-8">
        <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">收银台</h1>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="p-6 border-b border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">订单编号：{{ orderId }}</p>
              <p class="text-sm text-gray-500">剩余支付时间</p>
            </div>
            <div :class="['text-2xl font-mono font-bold tabular-nums', countdownSeconds < 300 ? 'text-red-600' : 'text-gray-900']">
              {{ formattedCountdown }}
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-100 flex items-baseline gap-2">
            <span class="text-sm text-gray-500">应付金额</span>
            <span class="text-4xl font-bold text-red-600">
              <span class="text-xl">&yen;</span>{{ formatPrice(orderAmount) }}
            </span>
          </div>
        </div>

        <div class="p-6">
          <h3 class="text-sm font-medium text-gray-700 mb-4">选择支付方式</h3>
          <div class="space-y-3">
            <label
              v-for="method in payMethods"
              :key="method.key"
              :class="['flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all', selectedPayMethod === method.key ? 'border-red-500 bg-red-50/30' : 'border-gray-200 hover:border-gray-300']"
            >
              <input v-model="selectedPayMethod" type="radio" :value="method.key" class="w-4 h-4 text-red-600 focus:ring-red-500" />
              <div :class="['w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', method.iconBg]">
                <span class="text-white font-bold">{{ method.iconChar }}</span>
              </div>
              <div class="flex-1">
                <p class="text-sm font-medium text-gray-900">{{ method.label }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ method.desc }}</p>
              </div>
              <svg v-if="selectedPayMethod === method.key" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </label>
          </div>
        </div>

        <div class="px-6 pb-6">
          <div v-if="payError" class="text-sm text-red-600 text-center mb-3">{{ payError }}</div>
          <button
            :disabled="isExpired || paying"
            class="w-full h-14 bg-red-600 text-white text-lg font-bold rounded-lg hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-red-200"
            @click="handlePay"
          >
            <span v-if="paying" class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              支付处理中...
            </span>
            <span v-else-if="isExpired">订单已过期</span>
            <span v-else>确认支付 &yen;{{ formatPrice(orderAmount) }}</span>
          </button>
        </div>
      </div>

      <div class="flex items-center justify-center gap-4 mt-4 text-xs text-gray-400">
        <span class="flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
          SSL安全加密
        </span>
        <span class="flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
          支付安全保障
        </span>
      </div>
    </div>
  </div>
</template>
