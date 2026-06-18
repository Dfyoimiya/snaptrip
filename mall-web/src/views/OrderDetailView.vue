<script setup lang="ts">
/**
 * ============================================
 * 订单详情页 (OrderDetailView)
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOrderDetailAPI } from '@/apis/order'

const route = useRoute()
const router = useRouter()
const orderId = route.params.id as string

interface OrderItem {
  productName?: string
  productPic?: string
  price?: number
  quantity?: number
  productAttr?: string
  productId?: string
}

interface OrderDetail {
  id: string
  orderSn?: string
  status?: number
  createdAt?: string
  paymentTime?: string
  deliveryTime?: string
  receiveTime?: string
  payType?: number
  receiverName?: string
  receiverPhone?: string
  receiverDetailAddress?: string
  items?: OrderItem[]
  totalAmount?: number
  freightAmount?: number
  discountAmount?: number
  payAmount?: number
}

const order = ref<OrderDetail | null>(null)
const loading = ref(false)
const error = ref('')

const statusMap: Record<number, { label: string; class: string }> = {
  0: { label: '待付款', class: 'text-orange-600' },
  1: { label: '待发货', class: 'text-blue-600' },
  2: { label: '待收货', class: 'text-purple-600' },
  3: { label: '已完成', class: 'text-green-600' },
  4: { label: '已关闭', class: 'text-gray-400' },
}

const payTypeMap: Record<number, string> = {
  1: '支付宝', 2: '微信支付', 3: '银行卡',
}

const statusLabel = computed(() => {
  if (!order.value) return ''
  return statusMap[order.value.status ?? -1]?.label || '未知'
})

const steps = computed(() => {
  if (!order.value) return []
  return [
    { key: 'order', label: '提交订单', time: order.value.createdAt || '' },
    { key: 'pay', label: '已付款', time: order.value.paymentTime || '' },
    { key: 'ship', label: '已发货', time: order.value.deliveryTime || '' },
    { key: 'complete', label: '交易完成', time: order.value.receiveTime || '' },
  ]
})

const isStepComplete = (stepIdx: number) => {
  if (!order.value) return false
  return (order.value.status ?? 0) >= stepIdx
}

const progressPercent = computed(() => {
  if (!order.value) return 0
  const map = [0, 33, 66, 100, 0]
  return map[order.value.status ?? 0] || 0
})

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })

onMounted(async () => {
  if (!orderId) {
    error.value = '订单ID无效'
    return
  }
  loading.value = true
  try {
    order.value = (await getOrderDetailAPI(orderId)) as unknown as OrderDetail
  } catch {
    error.value = '加载订单详情失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="order-detail-page space-y-5">
    <nav class="flex items-center gap-2 text-sm text-gray-500">
      <button class="hover:text-red-600" @click="router.push('/member/orders')">我的订单</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-900 font-medium">订单详情</span>
    </nav>

    <div v-if="error && !loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">
      {{ error }}
    </div>

    <template v-else-if="order">
      <!-- 订单状态卡片 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h1 class="text-lg font-bold text-gray-900">
              订单号：{{ order.orderSn || order.id }}
              <span :class="['ml-3 text-sm px-2.5 py-1 rounded-full font-medium bg-gray-100', statusMap[order.status ?? -1]?.class || '']">
                {{ statusLabel }}
              </span>
            </h1>
            <p class="text-sm text-gray-400 mt-1">下单时间：{{ order.createdAt }}</p>
          </div>
          <div class="text-right">
            <p class="text-sm text-gray-500">应付金额</p>
            <p class="text-2xl font-bold text-red-600">&yen;{{ formatPrice(order.payAmount || 0) }}</p>
          </div>
        </div>

        <!-- 步骤条 -->
        <div class="relative px-4 mb-2">
          <div class="absolute top-5 left-16 right-16 h-1 bg-gray-100 rounded-full" />
          <div class="absolute top-5 left-16 h-1 bg-red-500 rounded-full transition-all duration-500" :style="{ width: `calc(${progressPercent}% - 32px)` }" />
          <div class="relative flex items-center justify-between">
            <div v-for="(step, index) in steps" :key="step.key" class="flex flex-col items-center" :style="{ width: index === 0 || index === steps.length - 1 ? 'auto' : '120px' }">
              <div :class="['w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-300', isStepComplete(index) ? 'bg-red-600 text-white shadow-lg shadow-red-200' : 'bg-gray-100 text-gray-300']">
                <svg v-if="isStepComplete(index)" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div class="mt-2 text-center">
                <p :class="['text-sm font-medium', isStepComplete(index) ? 'text-gray-900' : 'text-gray-400']">{{ step.label }}</p>
                <p v-if="step.time" class="text-xs text-gray-400 mt-0.5">{{ step.time }}</p>
                <p v-else class="text-xs text-gray-300 mt-0.5">等待中</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 收货信息 & 支付信息 -->
      <div class="grid grid-cols-2 gap-5">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-bold text-gray-900 mb-3">收货信息</h3>
          <div class="space-y-2 text-sm">
            <p><span class="text-gray-500">收货人：</span><span class="text-gray-900">{{ order.receiverName }} {{ order.receiverPhone }}</span></p>
            <p><span class="text-gray-500">地址：</span><span class="text-gray-900">{{ order.receiverDetailAddress }}</span></p>
          </div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-bold text-gray-900 mb-3">支付信息</h3>
          <div class="space-y-2 text-sm">
            <p><span class="text-gray-500">支付方式：</span><span class="text-gray-900">{{ payTypeMap[order.payType ?? 0] || '未支付' }}</span></p>
            <p><span class="text-gray-500">支付时间：</span><span class="text-gray-900">{{ order.paymentTime || '未支付' }}</span></p>
          </div>
        </div>
      </div>

      <!-- 商品清单 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100">
          <h3 class="text-sm font-bold text-gray-900">商品清单</h3>
        </div>
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500">
            <tr>
              <th class="text-left px-6 py-3 font-medium">商品</th>
              <th class="text-center w-28 font-medium">单价</th>
              <th class="text-center w-20 font-medium">数量</th>
              <th class="text-right w-28 pr-6 font-medium">小计</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="(item, i) in order.items || []" :key="i" class="hover:bg-gray-50/30">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <img v-if="item.productPic" :src="item.productPic" :alt="item.productName" class="w-14 h-14 rounded-lg object-cover border border-gray-100" />
                  <div v-else class="w-14 h-14 rounded-lg bg-gray-100 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ item.productName }}</p>
                    <p v-if="item.productAttr" class="text-xs text-gray-400 mt-0.5">{{ item.productAttr }}</p>
                  </div>
                </div>
              </td>
              <td class="text-center text-gray-600">&yen;{{ formatPrice(item.price || 0) }}</td>
              <td class="text-center text-gray-600">{{ item.quantity }}</td>
              <td class="text-right pr-6 font-bold text-red-600">&yen;{{ formatPrice((item.price || 0) * (item.quantity || 0)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 费用明细 -->
      <div class="flex justify-end">
        <div class="w-[380px] bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 class="text-sm font-bold text-gray-900 mb-4">费用明细</h3>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">商品总价</span>
              <span class="text-gray-900">&yen;{{ formatPrice(order.totalAmount || 0) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">运费</span>
              <span class="text-green-600">{{ (order.freightAmount || 0) === 0 ? '免运费' : '&yen;' + formatPrice(order.freightAmount || 0) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">优惠</span>
              <span class="text-red-600">-&yen;{{ formatPrice(order.discountAmount || 0) }}</span>
            </div>
            <div class="border-t border-gray-100 pt-3 flex justify-between">
              <span class="text-gray-900 font-medium">应付金额</span>
              <span class="text-2xl font-bold text-red-600">&yen;{{ formatPrice(order.payAmount || 0) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}
.animate-pulse {
  animation: pulse 2s infinite;
}
</style>
