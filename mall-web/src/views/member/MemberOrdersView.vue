<script setup lang="ts">
/**
 * ============================================
 * 我的订单页 (MemberOrdersView)
 * 个人中心子路由：状态 Tabs + 订单列表 + 操作按钮
 * 点击详情进入 OrderDetailView 查看步骤条
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOrderListAPI, cancelUserOrderAPI, confirmReceiveOrderAPI, payOrderAPI } from '@/apis/order'
import type { OmsOrderDetail } from '@/types/order'

const router = useRouter()

const loading = ref(false)

/** 状态筛选 */
const activeStatus = ref(-1)
const statusOptions = [
  { label: '全部', value: -1 },
  { label: '待付款', value: 0, color: 'text-orange-600' },
  { label: '待发货', value: 1, color: 'text-blue-600' },
  { label: '待收货', value: 2, color: 'text-purple-600' },
  { label: '已完成', value: 3, color: 'text-green-600' },
  { label: '已取消', value: 4, color: 'text-gray-400' },
]

/** 状态映射 */
const statusMap: Record<number, { text: string; color: string; bg: string; border: string }> = {
  0: { text: '待付款', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-100' },
  1: { text: '待发货', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100' },
  2: { text: '待收货', color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-100' },
  3: { text: '已完成', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-100' },
  4: { text: '已取消', color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-100' },
}

const orders = ref<OmsOrderDetail[]>([])

async function loadOrders() {
  loading.value = true
  try {
    const params: { page?: number; page_size?: number; status?: number } = { page: 1, page_size: 50 }
    if (activeStatus.value >= 0) params.status = activeStatus.value
    const res = await getOrderListAPI(params)
    orders.value = (res as unknown as { items: OmsOrderDetail[] }).items || []
  } catch (err: any) {
    console.error('加载订单失败:', err?.message || err)
  } finally {
    loading.value = false
  }
}

/** 拼接地址 */
function fullAddress(o: OmsOrderDetail): string {
  return [o.receiverProvince, o.receiverCity, o.receiverRegion, o.receiverDetailAddress].filter(Boolean).join('')
}

/** 规格文本 */
function specText(item: OmsOrderDetail['items'][number]): string {
  if (!item.productAttr || item.productAttr === '[]') return ''
  try {
    const parsed = JSON.parse(item.productAttr)
    if (Array.isArray(parsed)) return parsed.map((a: { value: string }) => a.value).join(' / ')
    return item.productAttr
  } catch { return item.productAttr }
}

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })

/** 获取各状态订单数量 */
const getStatusCount = (status: number) => orders.value.filter(o => o.status === status).length

/** 操作按钮 */
const getActions = (status: number) => {
  if (status === 0) return [{ label: '立即付款', type: 'primary' }, { label: '取消订单', type: 'danger' }]
  if (status === 1) return [{ label: '催发货', type: 'normal' }]
  if (status === 2) return [{ label: '确认收货', type: 'primary' }]
  if (status === 3) return [{ label: '评价', type: 'normal' }, { label: '申请售后', type: 'normal' }]
  return []
}

/** 查看订单详情 */
const viewDetail = (orderId: string) => {
  router.push(`/order/${orderId}`)
}

/** 处理订单操作按钮点击 */
const handleAction = async (order: OmsOrderDetail, action: { label: string; type: string }) => {
  const orderId = String(order.id)
  try {
    switch (action.label) {
      case '立即付款':
        await payOrderAPI(orderId)
        break
      case '取消订单':
        if (!confirm('确定要取消该订单吗？')) return
        await cancelUserOrderAPI(orderId)
        break
      case '确认收货':
        if (!confirm('确认已收到商品吗？')) return
        await confirmReceiveOrderAPI(orderId)
        break
      default:
        // 催发货、评价、申请售后等暂时只刷新列表
        break
    }
    await loadOrders()
  } catch (err: any) {
    alert(err?.message || '操作失败')
  }
}

onMounted(() => {
  loadOrders()
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <!-- 标题 -->
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
      <h2 class="text-lg font-bold text-gray-900">我的订单</h2>
      <span class="text-sm text-gray-400">共 {{ orders.length }} 个订单</span>
    </div>

    <!-- 状态 Tabs -->
    <div class="flex items-center gap-1 px-6 py-3 border-b border-gray-100 overflow-x-auto">
      <button
        v-for="opt in statusOptions"
        :key="opt.value"
        :class="[
          'px-4 py-2 text-sm rounded-lg transition-colors whitespace-nowrap flex-shrink-0',
          activeStatus === opt.value ? 'bg-brand-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100',
        ]"
        @click="activeStatus = opt.value; loadOrders()"
      >
        {{ opt.label }}
        <span v-if="opt.value >= 0 && getStatusCount(opt.value) > 0" class="ml-1 text-xs opacity-70">
          ({{ getStatusCount(opt.value) }})
        </span>
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex justify-center py-20 text-gray-400">加载中...</div>

    <!-- 订单列表 -->
    <div v-else class="divide-y divide-gray-50">
      <div
        v-for="order in orders"
        :key="order.id"
        class="px-6 py-5 hover:bg-gray-50/30 transition-colors"
      >
        <!-- 订单头部 -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3 text-sm">
            <span class="text-gray-500 font-mono">{{ order.orderSn }}</span>
            <span class="text-gray-300">|</span>
            <span class="text-gray-400">{{ order.createdAt }}</span>
          </div>
          <span :class="['text-xs px-2.5 py-1 rounded-full font-medium border', statusMap[order.status]?.bg, statusMap[order.status]?.border, statusMap[order.status]?.color]">
            {{ statusMap[order.status]?.text }}
          </span>
        </div>

        <!-- 商品列表 -->
        <div class="space-y-2">
          <div
            v-for="(item, i) in order.items"
            :key="i"
            class="flex items-center gap-3"
          >
            <img :src="item.productPic" :alt="item.productName" class="w-14 h-14 rounded-lg border border-gray-100 object-cover" />
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-800 truncate">{{ item.productName }}</p>
              <p v-if="specText(item)" class="text-xs text-gray-400 mt-0.5">{{ specText(item) }}</p>
            </div>
            <div class="text-right flex-shrink-0">
              <span class="text-sm font-medium text-gray-900">&yen;{{ formatPrice(item.price) }}</span>
              <span class="text-xs text-gray-400 ml-2">x{{ item.quantity }}</span>
            </div>
          </div>
        </div>

        <!-- 底部合计 + 操作 -->
        <div class="flex items-center justify-between mt-4 pt-3 border-t border-gray-50">
          <div class="text-sm text-gray-500">
            共 {{ order.items.reduce((s, i) => s + i.quantity, 0) }} 件商品
            <span class="mx-2">|</span>
            <span>收货人：{{ order.receiverName }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-gray-500">
              合计：<span class="text-lg font-bold text-gray-900">&yen;{{ formatPrice(order.payAmount) }}</span>
            </span>
            <button
              class="text-sm text-gray-600 hover:text-brand-600 px-3 py-1.5 border border-gray-200 rounded hover:border-brand-300 transition-colors"
              @click="viewDetail(order.id)"
            >
              查看详情
            </button>
            <button
              v-for="action in getActions(order.status)"
              :key="action.label"
              :class="[
                'text-sm px-4 py-1.5 rounded transition-colors',
                action.type === 'primary'
                  ? 'bg-brand-600 text-white hover:bg-brand-700'
                  : action.type === 'danger'
                    ? 'border border-red-200 text-red-600 hover:bg-red-50'
                    : 'border border-gray-200 text-gray-600 hover:bg-gray-50',
              ]"
              @click="handleAction(order, action)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="orders.length === 0" class="flex flex-col items-center justify-center py-20 text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p>暂无该状态的订单</p>
      </div>
    </div>
  </div>
</template>
