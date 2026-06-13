<script setup lang="ts">
/**
 * ============================================
 * 我的订单页 (MemberOrdersView)
 * 个人中心子路由：状态 Tabs + 订单列表 + 操作按钮
 * 点击详情进入 OrderDetailView 查看步骤条
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

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

interface OrderItem {
  name: string
  pic: string
  price: number
  qty: number
  spec?: string
}

interface Order {
  id: string
  status: number
  createTime: string
  items: OrderItem[]
  totalAmount: number
  freight: number
  discount: number
  receiver: string
  phone: string
  address: string
}

const orders = ref<Order[]>([
  {
    id: 'ORD20260608001', status: 0, createTime: '2026-06-08 14:32:18',
    items: [
      { name: 'Apple MacBook Air M3 16+512G', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=80&h=80&fit=crop', price: 9999, qty: 1, spec: '午夜色 / 16GB+512GB' },
      { name: 'Dyson HD15 吹风机', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=80&h=80&fit=crop', price: 2590, qty: 1, spec: '镍灰色' },
    ],
    totalAmount: 12588, freight: 0, discount: 0,
    receiver: '张三', phone: '13800138000', address: '上海市浦东新区陆家嘴环路1000号',
  },
  {
    id: 'ORD20260607002', status: 2, createTime: '2026-06-07 09:15:42',
    items: [
      { name: 'SK-II 神仙水 230ml', pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=80&h=80&fit=crop', price: 1540, qty: 2, spec: '230ml 标准装' },
    ],
    totalAmount: 3080, freight: 0, discount: 0,
    receiver: '张三', phone: '13800138000', address: '上海市浦东新区陆家嘴环路1000号',
  },
  {
    id: 'ORD20260606003', status: 3, createTime: '2026-06-06 20:08:56',
    items: [
      { name: 'Nike Air Force 1 白色 42码', pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=80&h=80&fit=crop', price: 749, qty: 1, spec: '白色 / 42码' },
    ],
    totalAmount: 749, freight: 0, discount: 0,
    receiver: '李四', phone: '13900139000', address: '北京市朝阳区建国路88号',
  },
  {
    id: 'ORD20260604005', status: 1, createTime: '2026-06-04 16:45:21',
    items: [
      { name: 'Sony WH-1000XM5 降噪耳机', pic: 'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=80&h=80&fit=crop', price: 1999, qty: 1, spec: '铂金银' },
    ],
    totalAmount: 1999, freight: 0, discount: 0,
    receiver: '张三', phone: '13800138000', address: '上海市浦东新区陆家嘴环路1000号',
  },
  {
    id: 'ORD20260603006', status: 3, createTime: '2026-06-03 11:23:37',
    items: [
      { name: '小米14 Pro 16GB+512GB 黑色', pic: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=80&h=80&fit=crop', price: 5499, qty: 1, spec: '黑色 / 16GB+512GB' },
    ],
    totalAmount: 5499, freight: 0, discount: 0,
    receiver: '王五', phone: '13700137000', address: '深圳市南山区科技园科苑路15号',
  },
])

const filteredOrders = computed(() => {
  if (activeStatus.value === -1) return orders.value
  return orders.value.filter(o => o.status === activeStatus.value)
})

const formatPrice = (p: number) => p.toLocaleString('zh-CN', { minimumFractionDigits: 2 })

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
          activeStatus === opt.value ? 'bg-red-600 text-white font-medium' : 'text-gray-600 hover:bg-gray-100',
        ]"
        @click="activeStatus = opt.value"
      >
        {{ opt.label }}
        <span v-if="opt.value >= 0 && getStatusCount(opt.value) > 0" class="ml-1 text-xs opacity-70">
          ({{ getStatusCount(opt.value) }})
        </span>
      </button>
    </div>

    <!-- 订单列表 -->
    <div class="divide-y divide-gray-50">
      <div
        v-for="order in filteredOrders"
        :key="order.id"
        class="px-6 py-5 hover:bg-gray-50/30 transition-colors"
      >
        <!-- 订单头部 -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3 text-sm">
            <span class="text-gray-500 font-mono">{{ order.id }}</span>
            <span class="text-gray-300">|</span>
            <span class="text-gray-400">{{ order.createTime }}</span>
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
            <img :src="item.pic" :alt="item.name" class="w-14 h-14 rounded-lg border border-gray-100 object-cover" />
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-800 truncate">{{ item.name }}</p>
              <p class="text-xs text-gray-400 mt-0.5">{{ item.spec }}</p>
            </div>
            <div class="text-right flex-shrink-0">
              <span class="text-sm font-medium text-gray-900">&yen;{{ formatPrice(item.price) }}</span>
              <span class="text-xs text-gray-400 ml-2">x{{ item.qty }}</span>
            </div>
          </div>
        </div>

        <!-- 底部合计 + 操作 -->
        <div class="flex items-center justify-between mt-4 pt-3 border-t border-gray-50">
          <div class="text-sm text-gray-500">
            共 {{ order.items.reduce((s, i) => s + i.qty, 0) }} 件商品
            <span class="mx-2">|</span>
            <span>收货人：{{ order.receiver }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-gray-500">
              合计：<span class="text-lg font-bold text-gray-900">&yen;{{ formatPrice(order.totalAmount) }}</span>
            </span>
            <button
              class="text-sm text-gray-600 hover:text-red-600 px-3 py-1.5 border border-gray-200 rounded hover:border-red-300 transition-colors"
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
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : action.type === 'danger'
                    ? 'border border-red-200 text-red-600 hover:bg-red-50'
                    : 'border border-gray-200 text-gray-600 hover:bg-gray-50',
              ]"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredOrders.length === 0" class="flex flex-col items-center justify-center py-20 text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p>暂无该状态的订单</p>
      </div>
    </div>
  </div>
</template>
