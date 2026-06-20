<script setup lang="ts">
/**
 * ============================================
 * 订单详情页 (OrderDetailView) — 淘宝式布局
 * 左 2/3：状态步骤条 → 状态Banner → 物流 → 店铺 → 商品横向 → 操作按钮
 * 右 1/3：付款详情 → 订单信息 → 收货信息
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOrderDetailAPI, cancelUserOrderAPI, confirmReceiveOrderAPI, payOrderAPI } from '@/apis/order'

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
  spec?: string
}
interface OrderDetail {
  id: string; orderSn?: string; status?: number; createdAt?: string
  paymentTime?: string; deliveryTime?: string; receiveTime?: string
  payType?: number; receiverName?: string; receiverPhone?: string
  receiverDetailAddress?: string; receiverProvince?: string; receiverCity?: string; receiverRegion?: string
  items?: OrderItem[]; totalAmount?: number; freightAmount?: number
  discountAmount?: number; payAmount?: number; deliveryCompany?: string; deliverySn?: string
}

const order = ref<OrderDetail | null>(null)
const loading = ref(false)
const error = ref('')

// ============================================================
// 状态常量
// ============================================================
const STATUS_LABEL: Record<number, string> = {
  0: '待付款', 1: '待发货', 2: '待收货', 3: '已收货',
  4: '已完成', 5: '已关闭', 6: '退款中', 7: '已退款',
}

const STATUS_BANNER: Record<number, { title: string; sub: string; icon: string; color: string; bg: string }> = {
  0: { title: '等待买家付款', sub: '订单已提交，请尽快完成支付', icon: '💰', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' },
  1: { title: '买家已付款', sub: '卖家正在准备发货，请耐心等待', icon: '📦', color: 'text-orange-600', bg: 'bg-orange-50 border-orange-200' },
  2: { title: '卖家已发货', sub: '商品正在路上，请注意查收', icon: '🚚', color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200' },
  3: { title: '已确认收货', sub: '交易即将完成', icon: '✅', color: 'text-green-600', bg: 'bg-green-50 border-green-200' },
  4: { title: '交易已完成', sub: '感谢您的购买，欢迎再次光临', icon: '🎉', color: 'text-green-600', bg: 'bg-green-50 border-green-200' },
  5: { title: '交易已关闭', sub: '该订单已被关闭', icon: '⛔', color: 'text-gray-400', bg: 'bg-gray-50 border-gray-200' },
  6: { title: '退款处理中', sub: '退款正在处理，请耐心等待', icon: '🔄', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' },
  7: { title: '已退款', sub: '退款已完成', icon: '💵', color: 'text-gray-400', bg: 'bg-gray-50 border-gray-200' },
}

const PAY_TYPE_MAP: Record<number, string> = { 1: '支付宝', 2: '微信支付', 3: '银行卡' }

// ============================================================
// 步骤条
// ============================================================
const stepItems = ['拍下宝贝', '买家付款', '卖家发货', '确认收货', '交易完成']

const activeStep = computed(() => {
  const s = order.value?.status ?? 0
  if (s >= 5 && s <= 7) return -1 // closed/refunding/refunded — don't show normal steps
  if (s >= 4) return 4
  return s
})

const isStepDone = (idx: number) => (order.value?.status ?? 0) > idx

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
const formatDate = (d: string | null | undefined) => {
  if (!d) return ''
  return d.replace('T', ' ').substring(0, 19)
}

// ============================================================
// 数据加载
// ============================================================
onMounted(async () => {
  if (!orderId) { error.value = '订单ID无效'; return }
  loading.value = true
  try {
    const res = await getOrderDetailAPI(orderId)
    order.value = (res as any).data || res
  } catch {
    error.value = '加载订单详情失败'
  } finally {
    loading.value = false
  }
})

// ============================================================
// 操作
// ============================================================
const acting = ref(false)
async function handlePay() {
  if (acting.value) return
  acting.value = true
  try {
    await payOrderAPI(orderId)
    window.location.reload()
  } catch { /* ignore */ }
  finally { acting.value = false }
}
async function handleCancel() {
  if (!confirm('确定取消该订单？')) return
  try {
    await cancelUserOrderAPI(orderId)
    window.location.reload()
  } catch { /* ignore */ }
}
async function handleConfirmReceipt() {
  if (!confirm('确认已收到商品？')) return
  try {
    await confirmReceiveOrderAPI(orderId)
    window.location.reload()
  } catch { /* ignore */ }
}
function handleBuyAgain() {
  router.push('/')
}
function handleViewLogistics() {
  // mock — just show the info
  alert(`物流公司：${order.value?.deliveryCompany || '--'}\n运单号：${order.value?.deliverySn || '--'}`)
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-6 space-y-4">

    <!-- 面包屑 -->
    <nav class="flex items-center gap-2 text-sm text-gray-500">
      <button class="hover:text-orange-600" @click="router.push('/member/orders')">我的订单</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-900 font-medium">订单详情</span>
    </nav>

    <!-- 错误态 -->
    <div v-if="error && !loading" class="bg-white rounded-xl shadow-sm border border-gray-100 p-20 text-center text-gray-400">{{ error }}</div>

    <template v-else-if="order">
      <!-- ========== 左右布局 ========== -->
      <div class="flex gap-4 items-start">

        <!-- ========== 左侧 2/3 ========== -->
        <div class="flex-[2] min-w-0 space-y-3">

          <!-- 步骤条 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div v-if="activeStep >= 0" class="relative px-2">
              <div class="absolute top-4 left-8 right-8 h-0.5 bg-gray-200 rounded" />
              <div class="absolute top-4 left-8 h-0.5 bg-orange-500 rounded transition-all duration-500"
                :style="{ width: `calc(${(activeStep / 4) * 100}% - 16px)` }" />
              <div class="relative flex justify-between">
                <div v-for="(step, idx) in stepItems" :key="idx"
                  class="flex flex-col items-center z-10"
                  :style="{ width: idx === 0 || idx === 4 ? 'auto' : '80px' }">
                  <div :class="[
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
                    isStepDone(idx) ? 'bg-orange-500 text-white' :
                    activeStep === idx ? 'bg-orange-500 text-white ring-4 ring-orange-100' :
                    'bg-gray-100 text-gray-400'
                  ]">
                    <span v-if="isStepDone(idx)">✓</span>
                    <span v-else>{{ idx + 1 }}</span>
                  </div>
                  <span :class="['text-xs mt-1.5 whitespace-nowrap', isStepDone(idx) || activeStep === idx ? 'text-gray-900 font-medium' : 'text-gray-400']">
                    {{ step }}
                  </span>
                </div>
              </div>
            </div>
            <!-- 已关闭/退款中/已退款 特殊状态 -->
            <div v-else class="flex flex-col items-center py-4">
              <span class="text-4xl">{{ STATUS_BANNER[order.status ?? 5]?.icon || '⛔' }}</span>
              <span :class="['text-lg font-bold mt-2', STATUS_BANNER[order.status ?? 5]?.color || 'text-gray-400']">
                {{ STATUS_BANNER[order.status ?? 5]?.title || '--' }}
              </span>
            </div>
          </div>

          <!-- 状态 Banner -->
          <div :class="[
            'rounded-xl border p-5 flex items-center gap-4',
            (STATUS_BANNER[order.status ?? 0]?.bg || 'bg-gray-50 border-gray-200')
          ]">
            <span class="text-3xl flex-shrink-0">{{ STATUS_BANNER[order.status ?? 0]?.icon || '📋' }}</span>
            <div class="flex-1 min-w-0">
              <p :class="['text-lg font-bold', STATUS_BANNER[order.status ?? 0]?.color || '']">
                {{ STATUS_BANNER[order.status ?? 0]?.title || '--' }}
              </p>
              <p class="text-sm text-gray-500 mt-0.5">{{ STATUS_BANNER[order.status ?? 0]?.sub || '' }}</p>
            </div>
            <span :class="['text-sm font-medium px-3 py-1 rounded-full', STATUS_BANNER[order.status ?? 0]?.bg || 'bg-gray-100']">
              {{ STATUS_LABEL[order.status ?? 0] || '--' }}
            </span>
          </div>

          <!-- 物流信息 (已发货/已收货/已完成) -->
          <div v-if="order.deliveryCompany && (order.status ?? 0) >= 2 && (order.status ?? 0) <= 4"
            class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="text-blue-500 text-xl">📬</span>
              <div>
                <p class="text-sm font-medium text-gray-900">{{ order.deliveryCompany }}</p>
                <p class="text-xs text-gray-500 mt-0.5">运单号：{{ order.deliverySn }}</p>
              </div>
            </div>
            <button @click="handleViewLogistics" class="text-sm text-blue-600 hover:text-blue-700 whitespace-nowrap">查看物流 →</button>
          </div>

          <!-- 店铺 -->
          <div class="bg-white rounded-t-xl shadow-sm border border-gray-100 border-b-0 p-3 flex items-center gap-2">
            <div class="w-7 h-7 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center font-bold">店</div>
            <span class="text-sm font-medium text-gray-900">SnapTrip 商城</span>
            <span class="text-gray-300 text-xs">›</span>
          </div>

          <!-- 商品列表 -->
          <div class="bg-white rounded-b-xl shadow-sm border border-gray-100 border-t-0 overflow-hidden">
            <div v-for="(item, i) in order.items || []" :key="i"
              class="flex items-center gap-4 px-4 py-3 border-b border-gray-50 last:border-b-0 hover:bg-gray-50/30 transition-colors">
              <img v-if="item.productPic" :src="item.productPic" :alt="item.productName"
                class="w-16 h-16 rounded-lg object-cover border border-gray-100 flex-shrink-0" />
              <div v-else class="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 text-gray-300 text-xl">📷</div>
              <div class="flex-1 min-w-0">
                <a href="javascript:void(0)" class="text-sm text-gray-900 hover:text-orange-600 line-clamp-2 leading-snug">{{ item.productName }}</a>
                <p v-if="item.spec || item.productAttr" class="text-xs text-gray-400 mt-1">{{ item.spec || item.productAttr }}</p>
              </div>
              <div class="text-sm text-gray-600 w-16 text-center">¥{{ item.price }}</div>
              <div class="text-sm text-gray-500 w-10 text-center">×{{ item.quantity }}</div>
              <div class="text-sm font-semibold text-gray-900 w-20 text-right">¥{{ formatPrice((item.price || 0) * (item.quantity || 0)) }}</div>
            </div>
            <div v-if="!order.items?.length" class="px-4 py-10 text-center text-gray-400 text-sm">暂无商品信息</div>
          </div>

          <!-- 操作按钮 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex justify-end gap-3">
            <!-- 待付款 -->
            <template v-if="order.status === 0">
              <button @click="handleCancel" class="px-6 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium transition-colors">取消订单</button>
              <button @click="handlePay" :disabled="acting"
                class="px-8 py-2.5 rounded-lg bg-orange-500 text-white hover:bg-orange-600 text-sm font-bold transition-colors disabled:opacity-50">
                {{ acting ? '处理中...' : '立即付款' }}
              </button>
            </template>
            <!-- 待发货 -->
            <template v-if="order.status === 1">
              <span class="text-sm text-gray-500 self-center">等待卖家发货...</span>
            </template>
            <!-- 已发货 -->
            <template v-if="order.status === 2">
              <button @click="handleViewLogistics" class="px-6 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium transition-colors">查看物流</button>
              <button @click="handleConfirmReceipt"
                class="px-8 py-2.5 rounded-lg bg-orange-500 text-white hover:bg-orange-600 text-sm font-bold transition-colors">确认收货</button>
            </template>
            <!-- 已完成 -->
            <template v-if="order.status === 3 || order.status === 4">
              <button @click="handleBuyAgain"
                class="px-8 py-2.5 rounded-lg bg-orange-500 text-white hover:bg-orange-600 text-sm font-bold transition-colors">再次购买</button>
            </template>
            <!-- 已退款 -->
            <template v-if="order.status === 7">
              <button @click="handleBuyAgain"
                class="px-8 py-2.5 rounded-lg bg-orange-500 text-white hover:bg-orange-600 text-sm font-bold transition-colors">再次购买</button>
            </template>
          </div>
        </div>

        <!-- ========== 右侧 1/3 ========== -->
        <div class="flex-1 min-w-[300px] max-w-[380px] space-y-3 flex-shrink-0">

          <!-- 付款详情 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="bg-gray-50 px-5 py-3 border-b border-gray-100">
              <h3 class="text-sm font-bold text-gray-900">付款详情</h3>
            </div>
            <div class="px-5 py-4 space-y-2.5 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-500">商品总额</span>
                <span class="text-gray-900">¥{{ formatPrice(order.totalAmount) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-500">运费</span>
                <span :class="(order.freightAmount || 0) === 0 ? 'text-green-600' : 'text-gray-900'">
                  {{ (order.freightAmount || 0) === 0 ? '免运费' : '¥' + formatPrice(order.freightAmount) }}
                </span>
              </div>
              <div v-if="order.discountAmount" class="flex justify-between">
                <span class="text-gray-500">优惠</span>
                <span class="text-green-600">-¥{{ formatPrice(order.discountAmount) }}</span>
              </div>
              <div class="border-t border-gray-200 pt-3 flex justify-between items-baseline">
                <span class="text-gray-900 font-medium">实付款</span>
                <span class="text-2xl font-bold text-orange-500">¥{{ formatPrice(order.payAmount) }}</span>
              </div>
            </div>
          </div>

          <!-- 订单信息 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="bg-gray-50 px-5 py-3 border-b border-gray-100">
              <h3 class="text-sm font-bold text-gray-900">订单信息</h3>
            </div>
            <div class="px-5 py-4 space-y-2.5 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-500">订单编号</span>
                <span class="text-gray-900 font-mono text-xs max-w-[180px] truncate">{{ order.orderSn || order.id }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-500">创建时间</span>
                <span class="text-gray-900 text-xs">{{ formatDate(order.createdAt) }}</span>
              </div>
              <div v-if="order.paymentTime" class="flex justify-between">
                <span class="text-gray-500">付款时间</span>
                <span class="text-gray-900 text-xs">{{ formatDate(order.paymentTime) }}</span>
              </div>
              <div v-if="order.deliveryTime" class="flex justify-between">
                <span class="text-gray-500">发货时间</span>
                <span class="text-gray-900 text-xs">{{ formatDate(order.deliveryTime) }}</span>
              </div>
              <div v-if="order.receiveTime" class="flex justify-between">
                <span class="text-gray-500">收货时间</span>
                <span class="text-gray-900 text-xs">{{ formatDate(order.receiveTime) }}</span>
              </div>
              <div class="flex justify-between" v-if="order.payType">
                <span class="text-gray-500">支付方式</span>
                <span class="text-gray-900">{{ PAY_TYPE_MAP[order.payType] || '--' }}</span>
              </div>
            </div>
          </div>

          <!-- 收货信息 -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="bg-gray-50 px-5 py-3 border-b border-gray-100">
              <h3 class="text-sm font-bold text-gray-900">收货信息</h3>
            </div>
            <div class="px-5 py-4 space-y-2 text-sm">
              <p class="text-gray-900">{{ order.receiverName }} <span class="text-gray-400 ml-2">{{ order.receiverPhone }}</span></p>
              <p class="text-gray-500 text-xs leading-relaxed">
                {{ order.receiverProvince || '' }}{{ order.receiverCity || '' }}{{ order.receiverRegion || '' }} {{ order.receiverDetailAddress || '' }}
              </p>
            </div>
          </div>

        </div>
      </div>
    </template>
  </div>
</template>
