<script setup lang="ts">
/**
 * ============================================
 * 确认订单页 (OrderConfirmView)
 * 宽屏结构：上方地址卡片并排 + 中间商品核对表格 + 右下方费用明细与提交按钮
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import type { MemberReceiveAddress } from '@/types/address'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()

// ===== 地址数据 =====
const addresses = ref<MemberReceiveAddress[]>([
  { id: 1, name: '张三', phoneNumber: '13800138000', defaultStatus: 1, province: '上海市', city: '上海市', region: '浦东新区', detailAddress: '陆家嘴环路1000号恒生银行大厦28楼' },
  { id: 2, name: '李四', phoneNumber: '13900139000', defaultStatus: 0, province: '北京市', city: '北京市', region: '朝阳区', detailAddress: '建国路88号SOHO现代城B座1502室' },
  { id: 3, name: '王五', phoneNumber: '13700137000', defaultStatus: 0, province: '广东省', city: '深圳市', region: '南山区', detailAddress: '科技园科苑路15号科兴科学园B栋3单元1201' },
])

const selectedAddressId = ref(1)
const selectedAddress = computed(() => addresses.value.find(a => a.id === selectedAddressId.value))
const submitting = ref(false)

// ===== 支付方式 =====
const payType = ref(1)

// ===== Mock 商品核对清单 =====
interface OrderItem {
  id: number
  name: string
  pic: string
  spec: string
  price: number
  quantity: number
}

const orderItems = ref<OrderItem[]>([
  { id: 1001, name: 'Apple MacBook Air M3芯片 13.6英寸 16GB+512GB', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=100&h=100&fit=crop', spec: '午夜色 / M3-10C / 16GB / 512GB', price: 9999, quantity: 1 },
  { id: 1002, name: 'Dyson Supersonic HD15 新一代吹风机 负离子护发', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=100&h=100&fit=crop', spec: '镍灰色', price: 2590, quantity: 1 },
  { id: 1003, name: 'Apple AirPods Pro 2 USB-C版 主动降噪', pic: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=100&h=100&fit=crop', spec: '白色 / MagSafe充电盒', price: 1899, quantity: 2 },
])

// ===== 金额计算 =====
/** 商品总价 */
const goodsTotal = computed(() => orderItems.value.reduce((s, i) => s + i.price * i.quantity, 0))
/** 运费 */
const freight = computed(() => goodsTotal.value >= 99 ? 0 : 10)
/** 优惠金额 */
const discount = computed(() => {
  // 满减：满10000减500，满8000减200
  if (goodsTotal.value >= 10000) return 500
  if (goodsTotal.value >= 8000) return 200
  return 0
})
/** 应付金额（精确计算） */
const payableAmount = computed(() => goodsTotal.value + freight.value - discount.value)

const formatPrice = (p: number) => p.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** 提交订单 */
const handleSubmitOrder = () => {
  if (!selectedAddress.value) {
    alert('请选择收货地址')
    return
  }
  submitting.value = true
  // 模拟提交
  setTimeout(() => {
    submitting.value = false
    // 生成订单号，跳转到收银台
    const orderId = 'ORD' + Date.now()
    router.push({
      path: '/pay',
      query: { orderId, amount: payableAmount.value },
    })
  }, 800)
}
</script>

<template>
  <div class="order-confirm-page space-y-5">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900">确认订单</h1>
      <button class="text-sm text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1" @click="router.push('/cart')">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        返回购物车
      </button>
    </div>

    <!-- ====== 收货地址（卡片式并排） ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          收货地址
        </h2>
        <span class="text-sm text-gray-400">{{ addresses.length }} 个地址</span>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div
          v-for="addr in addresses"
          :key="addr.id"
          :class="[
            'relative p-4 rounded-lg border-2 cursor-pointer transition-all',
            selectedAddressId === addr.id
              ? 'border-red-500 bg-red-50/30 shadow-sm'
              : 'border-gray-200 bg-white hover:border-gray-300',
          ]"
          @click="selectedAddressId = addr.id"
        >
          <!-- 选中标记 -->
          <div v-if="selectedAddressId === addr.id" class="absolute top-2 right-2">
            <div class="w-5 h-5 rounded-full bg-red-600 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <div class="flex items-center gap-2 mb-1.5">
            <span class="text-sm font-bold text-gray-900">{{ addr.name }}</span>
            <span class="text-sm text-gray-500">{{ addr.phoneNumber }}</span>
          </div>
          <p class="text-xs text-gray-600 leading-5">
            {{ addr.province }} {{ addr.city }} {{ addr.region }} {{ addr.detailAddress }}
          </p>
          <span v-if="addr.defaultStatus === 1" class="inline-block mt-2 text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded font-medium">默认</span>
        </div>
      </div>
    </div>

    <!-- ====== 商品核对清单（表格） ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100">
        <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          商品清单（{{ orderItems.reduce((s, i) => s + i.quantity, 0) }} 件）
        </h2>
      </div>

      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="text-left px-6 py-3 font-medium">商品信息</th>
            <th class="text-center w-32 font-medium">单价</th>
            <th class="text-center w-24 font-medium">数量</th>
            <th class="text-right w-32 pr-6 font-medium">小计</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="item in orderItems" :key="item.id" class="hover:bg-gray-50/30">
            <td class="px-6 py-4">
              <div class="flex items-center gap-4">
                <img :src="item.pic" :alt="item.name" class="w-16 h-16 rounded-lg object-cover border border-gray-100" />
                <div>
                  <p class="text-sm font-medium text-gray-900 line-clamp-1">{{ item.name }}</p>
                  <p class="text-xs text-gray-400 mt-1">{{ item.spec }}</p>
                </div>
              </div>
            </td>
            <td class="text-center text-gray-600">&yen;{{ formatPrice(item.price) }}</td>
            <td class="text-center text-gray-600">{{ item.quantity }}</td>
            <td class="text-right pr-6 font-bold text-red-600">&yen;{{ formatPrice(item.price * item.quantity) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ====== 支付方式 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 class="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        支付方式
      </h2>
      <div class="flex items-center gap-4">
        <label
          :class="['flex items-center gap-3 px-5 py-3 border-2 rounded-lg cursor-pointer transition-all', payType === 1 ? 'border-red-500 bg-red-50/30' : 'border-gray-200 hover:border-gray-300']"
        >
          <input v-model="payType" type="radio" :value="1" class="w-4 h-4 text-red-600 focus:ring-red-500" />
          <div class="w-8 h-8 rounded bg-blue-500 flex items-center justify-center">
            <span class="text-white text-xs font-bold">支</span>
          </div>
          <div>
            <span class="text-sm font-medium text-gray-900">支付宝</span>
            <span class="text-xs text-gray-400 ml-2">推荐</span>
          </div>
        </label>
        <label
          :class="['flex items-center gap-3 px-5 py-3 border-2 rounded-lg cursor-pointer transition-all', payType === 2 ? 'border-red-500 bg-red-50/30' : 'border-gray-200 hover:border-gray-300']"
        >
          <input v-model="payType" type="radio" :value="2" class="w-4 h-4 text-red-600 focus:ring-red-500" />
          <div class="w-8 h-8 rounded bg-green-500 flex items-center justify-center">
            <span class="text-white text-xs font-bold">微</span>
          </div>
          <span class="text-sm font-medium text-gray-900">微信支付</span>
        </label>
      </div>
    </div>

    <!-- ====== 费用明细 + 提交按钮 ====== -->
    <div class="flex items-start gap-6">
      <!-- 备注 -->
      <div class="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">订单备注</h3>
        <textarea
          rows="3"
          placeholder="如有特殊要求，请在此备注（选填）"
          class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
        />
      </div>

      <!-- 费用明细 -->
      <div class="w-[380px] bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex-shrink-0">
        <h3 class="text-sm font-medium text-gray-700 mb-4">费用明细</h3>
        <div class="space-y-3 text-sm">
          <div class="flex items-center justify-between">
            <span class="text-gray-500">商品总价</span>
            <span class="text-gray-900 font-medium">&yen;{{ formatPrice(goodsTotal) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-500">运费</span>
            <span :class="freight === 0 ? 'text-green-600 font-medium' : 'text-gray-900 font-medium'">
              {{ freight === 0 ? '免运费' : '&yen;' + formatPrice(freight) }}
            </span>
          </div>
          <div v-if="discount > 0" class="flex items-center justify-between">
            <span class="text-gray-500">优惠</span>
            <span class="text-red-600 font-medium">-&yen;{{ formatPrice(discount) }}</span>
          </div>
          <div class="border-t border-gray-100 pt-3 mt-3">
            <div class="flex items-center justify-between">
              <span class="text-gray-900 font-medium">应付金额</span>
              <span class="text-2xl font-bold text-red-600">
                <span class="text-sm">&yen;</span>{{ formatPrice(payableAmount) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 提交订单按钮 -->
        <button
          :disabled="submitting"
          class="w-full mt-6 h-12 bg-red-600 text-white font-bold text-base rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors shadow-md shadow-red-200"
          @click="handleSubmitOrder"
        >
          {{ submitting ? '订单提交中...' : '提交订单' }}
        </button>

        <p class="text-xs text-gray-400 text-center mt-3">
          提交订单即表示您已阅读并同意 <span class="text-red-600">用户协议</span> 和 <span class="text-red-600">隐私政策</span>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-1 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
