<script setup lang="ts">
/**
 * ============================================
 * 确认订单页 (OrderConfirmView)
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { getAddressListAPI } from '@/apis/address'
import { generateOrderAPI } from '@/apis/order'
import type { MemberReceiveAddress } from '@/types/address'

const router = useRouter()
const cartStore = useCartStore()

const addresses = ref<MemberReceiveAddress[]>([])
const selectedAddressId = ref<string>('')
const submitting = ref(false)
const payType = ref(1)

interface CartItemView {
  id: string
  productName?: string
  productPic?: string
  productAttr?: string
  price: number
  quantity: number
  productId?: string
}

const orderItems = ref<CartItemView[]>([])

const selectedAddress = computed(() => addresses.value.find(a => String(a.id) === selectedAddressId.value))

const goodsTotal = computed(() => orderItems.value.reduce((s, i) => s + i.price * i.quantity, 0))
const freight = computed(() => goodsTotal.value >= 99 ? 0 : 10)
const discount = computed(() => {
  if (goodsTotal.value >= 10000) return 500
  if (goodsTotal.value >= 8000) return 200
  return 0
})
const payableAmount = computed(() => goodsTotal.value + freight.value - discount.value)

const formatPrice = (p: number | null | undefined) => (p ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

onMounted(async () => {
  try {
    const [addrList] = await Promise.all([
      getAddressListAPI(),
      cartStore.fetchCartList?.(),
    ])
    addresses.value = addrList || []
    if (addresses.value.length) {
      const defaultAddr = addresses.value.find(a => a.defaultStatus === 1)
      selectedAddressId.value = defaultAddr ? String(defaultAddr.id) : String(addresses.value[0].id)
    }

    // Get selected cart items (checked items from cart store)
    const cartItems = cartStore.cartList.filter(item => item.checked)
    orderItems.value = cartItems.map((item: any) => ({
      id: item.id,
      productName: item.productName || item.name,
      productPic: item.productPic || item.pic,
      productAttr: item.productAttr || item.spec,
      price: item.price || 0,
      quantity: item.quantity || 1,
      productId: item.productId,
    }))
  } catch {
    // addresses or cart might fail
  }
})

const handleSubmitOrder = async () => {
  if (!selectedAddress.value) {
    alert('请选择收货地址')
    return
  }
  if (orderItems.value.length === 0) {
    alert('购物车为空，请先添加商品')
    return
  }
  submitting.value = true
  try {
    const addr = selectedAddress.value
    const cartItemIds = cartStore.cartList.filter(item => item.checked).map(item => item.id)
    const result = await generateOrderAPI({
      cart_item_ids: cartItemIds,
      receiver_name: addr.name,
      receiver_phone: addr.phone,
      receiver_province: addr.province || '',
      receiver_city: addr.city || '',
      receiver_region: addr.region || '',
      receiver_detail_address: addr.detailAddress || '',
      receiver_post_code: addr.postCode || '',
      note: '',
      pay_type: payType.value,
      coupon_id: null,
    } as any)
    const orderData = result as any
    const orderId = orderData?.id || orderData?.orderId || ''
    router.push({
      path: '/pay',
      query: { orderId: String(orderId), amount: payableAmount.value },
    })
  } catch (e: any) {
    alert(e?.message || '提交订单失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="order-confirm-page space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900">确认订单</h1>
      <button class="text-sm text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1" @click="router.push('/cart')">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        返回购物车
      </button>
    </div>

    <!-- 收货地址 -->
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

      <div v-if="addresses.length" class="grid grid-cols-3 gap-4">
        <div
          v-for="addr in addresses"
          :key="addr.id"
          :class="['relative p-4 rounded-lg border-2 cursor-pointer transition-all', selectedAddressId === String(addr.id) ? 'border-red-500 bg-red-50/30 shadow-sm' : 'border-gray-200 bg-white hover:border-gray-300']"
          @click="selectedAddressId = String(addr.id)"
        >
          <div v-if="selectedAddressId === String(addr.id)" class="absolute top-2 right-2">
            <div class="w-5 h-5 rounded-full bg-red-600 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div class="flex items-center gap-2 mb-1.5">
            <span class="text-sm font-bold text-gray-900">{{ addr.name }}</span>
            <span class="text-sm text-gray-500">{{ addr.phone }}</span>
          </div>
          <p class="text-xs text-gray-600 leading-5">
            {{ addr.province }} {{ addr.city }} {{ addr.region }} {{ addr.detailAddress }}
          </p>
          <span v-if="addr.defaultStatus === 1" class="inline-block mt-2 text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded font-medium">默认</span>
        </div>
      </div>
      <div v-else class="text-center py-6 text-gray-400">
        暂无收货地址，请先添加地址
      </div>
    </div>

    <!-- 商品清单 -->
    <div v-if="orderItems.length" class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100">
        <h2 class="text-base font-bold text-gray-900">商品清单（{{ orderItems.reduce((s, i) => s + i.quantity, 0) }} 件）</h2>
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
                <img v-if="item.productPic" :src="item.productPic" :alt="item.productName" class="w-16 h-16 rounded-lg object-cover border border-gray-100" />
                <div v-else class="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900 line-clamp-1">{{ item.productName }}</p>
                  <p v-if="item.productAttr" class="text-xs text-gray-400 mt-1">{{ item.productAttr }}</p>
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

    <!-- 费用明细 + 提交 -->
    <div class="flex items-start gap-6">
      <div class="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">订单备注</h3>
        <textarea rows="3" placeholder="如有特殊要求，请在此备注（选填）" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent" />
      </div>

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
              <span class="text-2xl font-bold text-red-600"><span class="text-sm">&yen;</span>{{ formatPrice(payableAmount) }}</span>
            </div>
          </div>
        </div>

        <button
          :disabled="submitting || orderItems.length === 0"
          class="w-full mt-6 h-12 bg-red-600 text-white font-bold text-base rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors shadow-md shadow-red-200"
          @click="handleSubmitOrder"
        >
          {{ submitting ? '订单提交中...' : '提交订单' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-1 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
