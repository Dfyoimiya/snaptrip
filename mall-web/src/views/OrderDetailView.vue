<script setup lang="ts">
/**
 * ============================================
 * 订单详情跟踪页 (OrderDetailView)
 * 顶部横向步骤条：下单 -> 付款 -> 发货 -> 完成
 * 中部商品清单 + 底部费用明细
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const orderId = route.params.id as string

/** Mock 订单数据 */
const order = ref({
  id: orderId,
  status: 2,
  statusText: '待收货',
  statusColor: 'text-purple-600',
  createTime: '2026-06-08 14:32:18',
  payTime: '2026-06-08 14:35:42',
  shipTime: '2026-06-09 09:15:00',
  receiveTime: '',
  payType: 1,
  payTypeText: '支付宝',
  receiver: '张三',
  phone: '13800138000',
  address: '上海市浦东新区陆家嘴环路1000号恒生银行大厦28楼',
  items: [
    { name: 'Apple MacBook Air M3芯片 13.6英寸 16GB+512GB', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=100&h=100&fit=crop', price: 9999, qty: 1, spec: '午夜色 / M3-10C / 16GB / 512GB' },
    { name: 'Dyson Supersonic HD15 新一代吹风机', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=100&h=100&fit=crop', price: 2590, qty: 1, spec: '镍灰色' },
  ],
  goodsTotal: 12589,
  freight: 0,
  discount: 500,
  payable: 12089,
})

/** 步骤条数据 */
const steps = [
  { key: 'order', label: '提交订单', time: order.value.createTime, icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { key: 'pay', label: '已付款', time: order.value.payTime, icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z' },
  { key: 'ship', label: '已发货', time: order.value.shipTime, icon: 'M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0' },
  { key: 'complete', label: '交易完成', time: order.value.receiveTime, icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
]

/** 判断步骤是否完成 */
const isStepComplete = (stepKey: string) => {
  const stepMap: Record<string, number> = { order: 0, pay: 1, ship: 2, complete: 3 }
  return order.value.status >= stepMap[stepKey]
}

/** 判断步骤是否当前进行 */
const isStepActive = (stepKey: string) => {
  const stepMap: Record<string, number> = { order: 0, pay: 1, ship: 2, complete: 3 }
  const stepStatus = stepMap[stepKey]
  if (order.value.status === 4) return false
  return order.value.status >= stepStatus && (!steps[stepStatus + 1] || order.value.status < stepMap[steps[stepStatus + 1].key])
}

/** 当前进度百分比 */
const progressPercent = computed(() => {
  const map = [0, 33, 66, 100, 0]
  return map[order.value.status] || 0
})

const formatPrice = (p: number) => p.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
</script>

<template>
  <div class="order-detail-page space-y-5">
    <!-- 面包屑 -->
    <nav class="flex items-center gap-2 text-sm text-gray-500">
      <button class="hover:text-red-600" @click="router.push('/member/orders')">我的订单</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-900 font-medium">订单详情</span>
    </nav>

    <!-- ====== 订单状态卡片 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-lg font-bold text-gray-900">
            订单号：{{ order.id }}
            <span :class="['ml-3 text-sm px-2.5 py-1 rounded-full font-medium bg-gray-100', order.statusColor]">
              {{ order.statusText }}
            </span>
          </h1>
          <p class="text-sm text-gray-400 mt-1">下单时间：{{ order.createTime }}</p>
        </div>
        <div class="text-right">
          <p class="text-sm text-gray-500">应付金额</p>
          <p class="text-2xl font-bold text-red-600">&yen;{{ formatPrice(order.payable) }}</p>
        </div>
      </div>

      <!-- ====== 横向步骤条 ====== -->
      <div class="relative px-4 mb-2">
        <!-- 进度背景线 -->
        <div class="absolute top-5 left-16 right-16 h-1 bg-gray-100 rounded-full" />
        <!-- 进度填充线 -->
        <div
          class="absolute top-5 left-16 h-1 bg-red-500 rounded-full transition-all duration-500"
          :style="{ width: `calc(${progressPercent}% - 32px)` }"
        />

        <!-- 步骤节点 -->
        <div class="relative flex items-center justify-between">
          <div
            v-for="(step, index) in steps"
            :key="step.key"
            class="flex flex-col items-center"
            :style="{ width: index === 0 || index === steps.length - 1 ? 'auto' : '120px' }"
          >
            <!-- 步骤图标 -->
            <div
              :class="[
                'w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-300',
                isStepComplete(step.key)
                  ? 'bg-red-600 text-white shadow-lg shadow-red-200'
                  : isStepActive(step.key)
                    ? 'bg-red-100 text-red-600 border-2 border-red-500 animate-pulse'
                    : 'bg-gray-100 text-gray-300',
              ]"
            >
              <svg v-if="isStepComplete(step.key)" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" :d="step.icon" />
              </svg>
            </div>
            <!-- 步骤标签 -->
            <div class="mt-2 text-center">
              <p :class="['text-sm font-medium', isStepComplete(step.key) || isStepActive(step.key) ? 'text-gray-900' : 'text-gray-400']">
                {{ step.label }}
              </p>
              <p v-if="step.time" class="text-xs text-gray-400 mt-0.5">{{ step.time }}</p>
              <p v-else class="text-xs text-gray-300 mt-0.5">等待中</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 收货信息 ====== -->
    <div class="grid grid-cols-2 gap-5">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h3 class="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          收货信息
        </h3>
        <div class="space-y-2 text-sm">
          <p><span class="text-gray-500 w-16 inline-block">收货人：</span><span class="text-gray-900">{{ order.receiver }} {{ order.phone }}</span></p>
          <p><span class="text-gray-500 w-16 inline-block">地址：</span><span class="text-gray-900">{{ order.address }}</span></p>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h3 class="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          支付信息
        </h3>
        <div class="space-y-2 text-sm">
          <p><span class="text-gray-500 w-16 inline-block">支付方式：</span><span class="text-gray-900">{{ order.payTypeText }}</span></p>
          <p><span class="text-gray-500 w-16 inline-block">支付时间：</span><span class="text-gray-900">{{ order.payTime || '未支付' }}</span></p>
        </div>
      </div>
    </div>

    <!-- ====== 商品清单 ====== -->
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
          <tr v-for="(item, i) in order.items" :key="i" class="hover:bg-gray-50/30">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <img :src="item.pic" :alt="item.name" class="w-14 h-14 rounded-lg object-cover border border-gray-100" />
                <div>
                  <p class="text-sm font-medium text-gray-900">{{ item.name }}</p>
                  <p class="text-xs text-gray-400 mt-0.5">{{ item.spec }}</p>
                </div>
              </div>
            </td>
            <td class="text-center text-gray-600">&yen;{{ formatPrice(item.price) }}</td>
            <td class="text-center text-gray-600">{{ item.qty }}</td>
            <td class="text-right pr-6 font-bold text-red-600">&yen;{{ formatPrice(item.price * item.qty) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ====== 费用明细 ====== -->
    <div class="flex justify-end">
      <div class="w-[380px] bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 class="text-sm font-bold text-gray-900 mb-4">费用明细</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">商品总价</span>
            <span class="text-gray-900">&yen;{{ formatPrice(order.goodsTotal) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">运费</span>
            <span class="text-green-600">{{ order.freight === 0 ? '免运费' : '&yen;' + formatPrice(order.freight) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">优惠</span>
            <span class="text-red-600">-&yen;{{ formatPrice(order.discount) }}</span>
          </div>
          <div class="border-t border-gray-100 pt-3 flex justify-between">
            <span class="text-gray-900 font-medium">应付金额</span>
            <span class="text-2xl font-bold text-red-600">&yen;{{ formatPrice(order.payable) }}</span>
          </div>
        </div>
      </div>
    </div>
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
