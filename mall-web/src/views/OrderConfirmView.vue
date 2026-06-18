<script setup lang="ts">
/**
 * ============================================
 * 确认订单页 (OrderConfirmView)
 * — 淘宝式收货地址管理：选择/新增/编辑/删除
 * ============================================
 */
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { getAddressListAPI, addAddressAPI, updateAddressAPI, deleteAddressAPI } from '@/apis/address'
import { generateOrderAPI } from '@/apis/order'
import type { MemberReceiveAddress } from '@/types/address'

const router = useRouter()
const cartStore = useCartStore()

// ── 地址 ──
const addresses = ref<MemberReceiveAddress[]>([])
const selectedAddressId = ref<string>('')
const addressLoading = ref(false)

// ── 地址弹窗 ──
const addrDialogVisible = ref(false)
const addrDialogTitle = ref('新增收货地址')
const addrForm = reactive<MemberReceiveAddress>({
  name: '', phone: '', province: '', city: '', region: '',
  detailAddress: '', postCode: '', defaultStatus: 0,
})
const editingAddrId = ref<string | null>(null)
const addrSubmitting = ref(false)

// ── 删除确认 ──
const deleteConfirmId = ref<string | null>(null)

// ── 订单 ──
const submitting = ref(false)
const payType = ref(1)
const orderNote = ref('')

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

// ── 加载数据 ──
onMounted(async () => {
  try {
    const [addrList] = await Promise.all([
      getAddressListAPI(),
      cartStore.fetchCartList?.(),
    ])
    addresses.value = addrList || []
    if (addresses.value.length) {
      const defaultAddr = addresses.value.find(a => a.defaultStatus === 1)
      selectedAddressId.value = defaultAddr
        ? String(defaultAddr.id)
        : String(addresses.value[0].id)
    }

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

// ── 地址弹窗 ──
function openAddDialog(): void {
  addrDialogTitle.value = '新增收货地址'
  editingAddrId.value = null
  addrForm.name = ''
  addrForm.phone = ''
  addrForm.province = ''
  addrForm.city = ''
  addrForm.region = ''
  addrForm.detailAddress = ''
  addrForm.postCode = ''
  addrForm.defaultStatus = 0
  addrDialogVisible.value = true
}

function openEditDialog(addr: MemberReceiveAddress): void {
  addrDialogTitle.value = '编辑收货地址'
  editingAddrId.value = String(addr.id)
  addrForm.name = addr.name
  addrForm.phone = addr.phone
  addrForm.province = addr.province || ''
  addrForm.city = addr.city || ''
  addrForm.region = addr.region || ''
  addrForm.detailAddress = addr.detailAddress || ''
  addrForm.postCode = addr.postCode || ''
  addrForm.defaultStatus = addr.defaultStatus ?? 0
  addrDialogVisible.value = true
}

async function handleSaveAddress(): Promise<void> {
  if (!addrForm.name.trim() || !addrForm.phone.trim() || !addrForm.detailAddress.trim()) {
    alert('请填写收货人、联系电话和详细地址')
    return
  }
  addrSubmitting.value = true
  try {
    const payload = {
      name: addrForm.name.trim(),
      phone: addrForm.phone.trim(),
      province: addrForm.province.trim() || null,
      city: addrForm.city.trim() || null,
      region: addrForm.region.trim() || null,
      detail_address: addrForm.detailAddress.trim(),
      post_code: addrForm.postCode.trim() || null,
      default_status: addrForm.defaultStatus,
    }
    if (editingAddrId.value) {
      await updateAddressAPI(editingAddrId.value, payload)
    } else {
      await addAddressAPI(payload)
    }
    addrDialogVisible.value = false
    await reloadAddresses()
  } catch (e: any) {
    alert(e?.message || '保存失败')
  } finally {
    addrSubmitting.value = false
  }
}

async function handleDeleteAddress(addrId: string): Promise<void> {
  try {
    await deleteAddressAPI(addrId)
    if (selectedAddressId.value === addrId) {
      selectedAddressId.value = ''
    }
    deleteConfirmId.value = null
    await reloadAddresses()
  } catch (e: any) {
    alert(e?.message || '删除失败')
  }
}

async function reloadAddresses(): Promise<void> {
  addressLoading.value = true
  try {
    const list = await getAddressListAPI()
    addresses.value = list || []
    // 如果当前无选中，自动选默认或第一个
    if (!selectedAddressId.value && addresses.value.length) {
      const defaultAddr = addresses.value.find(a => a.defaultStatus === 1)
      selectedAddressId.value = defaultAddr ? String(defaultAddr.id) : String(addresses.value[0].id)
    }
  } finally {
    addressLoading.value = false
  }
}

// ── 提交订单 ──
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
      note: orderNote.value,
      pay_type: payType.value,
      coupon_id: null,
    })
    const orderId = result.id
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
    <!-- 顶部导航 -->
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900">确认订单</h1>
      <button class="text-sm text-gray-500 hover:text-brand-600 transition-colors flex items-center gap-1" @click="router.push('/cart')">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        返回购物车
      </button>
    </div>

    <!-- 收货地址 — 淘宝式卡片选择 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          收货地址
        </h2>
        <span class="text-xs text-gray-400">共 {{ addresses.length }} 个地址</span>
      </div>

      <!-- 加载中 -->
      <div v-if="addressLoading" class="flex items-center justify-center py-10">
        <svg class="animate-spin h-6 w-6 text-brand-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <!-- 地址卡片网格 -->
      <div v-else class="grid grid-cols-3 gap-4">
        <!-- 现有地址卡片 -->
        <div
          v-for="addr in addresses"
          :key="addr.id"
          :class="[
            'relative group p-4 rounded-xl border-2 cursor-pointer transition-all duration-200',
            selectedAddressId === String(addr.id)
              ? 'border-brand-500 bg-brand-50/40 shadow-sm shadow-brand-100'
              : 'border-gray-200 bg-white hover:border-brand-200 hover:shadow-sm',
          ]"
          @click="selectedAddressId = String(addr.id)"
        >
          <!-- 选中标记 -->
          <div v-if="selectedAddressId === String(addr.id)" class="absolute top-3 right-3">
            <svg class="w-5 h-5 text-brand-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
            </svg>
          </div>

          <!-- 用户信息 -->
          <div class="flex items-center gap-2 mb-2 pr-6">
            <span class="text-sm font-bold text-gray-900">{{ addr.name }}</span>
            <span class="text-sm text-gray-500">{{ addr.phone }}</span>
          </div>

          <!-- 地址 -->
          <p class="text-xs text-gray-600 leading-relaxed mb-3 min-h-[36px]">
            {{ addr.province || '' }}{{ addr.city || '' }}{{ addr.region || '' }} {{ addr.detailAddress || '' }}
          </p>

          <!-- 底部：默认标签 + 操作按钮 -->
          <div class="flex items-center justify-between">
            <span v-if="addr.defaultStatus === 1" class="text-xs bg-brand-100 text-brand-600 px-2 py-0.5 rounded-full font-medium">
              默认
            </span>
            <span v-else />

            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                class="text-xs text-gray-400 hover:text-brand-600 px-2 py-1 rounded-md hover:bg-brand-50 transition-colors"
                @click.stop="openEditDialog(addr)"
              >
                编辑
              </button>
              <button
                v-if="addresses.length > 1"
                class="text-xs text-gray-400 hover:text-red-500 px-2 py-1 rounded-md hover:bg-red-50 transition-colors"
                @click.stop="deleteConfirmId = String(addr.id)"
              >
                删除
              </button>
            </div>
          </div>

          <!-- 删除确认 -->
          <div
            v-if="deleteConfirmId === String(addr.id)"
            class="absolute inset-0 bg-white/95 rounded-xl flex flex-col items-center justify-center gap-2 z-10"
          >
            <p class="text-sm text-gray-700">确定删除该地址？</p>
            <div class="flex gap-2">
              <button class="text-xs px-4 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors" @click.stop="handleDeleteAddress(String(addr.id))">
                删除
              </button>
              <button class="text-xs px-4 py-1.5 bg-gray-200 text-gray-600 rounded-lg hover:bg-gray-300 transition-colors" @click.stop="deleteConfirmId = null">
                取消
              </button>
            </div>
          </div>
        </div>

        <!-- 新增地址入口卡片 -->
        <button
          class="p-4 rounded-xl border-2 border-dashed border-gray-300 hover:border-brand-400 hover:bg-brand-50/30 transition-all text-center flex flex-col items-center justify-center gap-2 min-h-[120px] group"
          @click="openAddDialog"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-gray-300 group-hover:text-brand-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          <span class="text-sm text-gray-400 group-hover:text-brand-600 transition-colors">新增收货地址</span>
        </button>
      </div>
    </div>

    <!-- 商品清单 -->
    <div v-if="orderItems.length" class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100">
        <h2 class="text-base font-bold text-gray-900">商品清单（{{ orderItems.reduce((s, i) => s + i.quantity, 0) }} 件）</h2>
      </div>
      <div v-for="item in orderItems" :key="item.id" class="flex items-center gap-4 px-6 py-4 hover:bg-gray-50/30 border-b border-gray-50 last:border-0">
        <img v-if="item.productPic" :src="item.productPic" :alt="item.productName" class="w-16 h-16 rounded-lg object-cover border border-gray-100" />
        <div v-else class="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate">{{ item.productName }}</p>
          <p v-if="item.productAttr" class="text-xs text-gray-400 mt-0.5">{{ item.productAttr }}</p>
        </div>
        <div class="text-sm text-gray-500 w-24 text-center">&yen;{{ formatPrice(item.price) }}</div>
        <div class="text-sm text-gray-500 w-16 text-center">x{{ item.quantity }}</div>
        <div class="text-sm font-bold text-brand-600 w-24 text-right">&yen;{{ formatPrice(item.price * item.quantity) }}</div>
      </div>
    </div>

    <!-- 备注 + 费用明细 -->
    <div class="flex items-start gap-6">
      <div class="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">订单备注（选填）</h3>
        <textarea v-model="orderNote" rows="3" placeholder="如有特殊要求，请在此备注" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" />
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
            <span class="text-brand-600 font-medium">-&yen;{{ formatPrice(discount) }}</span>
          </div>
          <div class="border-t border-gray-100 pt-3 mt-3">
            <div class="flex items-center justify-between">
              <span class="text-gray-900 font-medium">应付金额</span>
              <span class="text-2xl font-bold text-brand-600"><span class="text-sm">&yen;</span>{{ formatPrice(payableAmount) }}</span>
            </div>
          </div>
        </div>

        <button
          :disabled="submitting || orderItems.length === 0"
          class="w-full mt-6 h-12 bg-brand-600 text-white font-bold text-base rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors shadow-md shadow-brand-200"
          @click="handleSubmitOrder"
        >
          {{ submitting ? '订单提交中...' : '提交订单' }}
        </button>
      </div>
    </div>

    <!-- ──────────────────────────────── -->
    <!-- 地址编辑弹窗                        -->
    <!-- ──────────────────────────────── -->
    <Teleport to="body">
      <Transition name="dialog">
        <div v-if="addrDialogVisible" class="fixed inset-0 z-50 flex items-center justify-center">
          <!-- 遮罩 -->
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="addrDialogVisible = false" />

          <!-- 弹窗 -->
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 max-h-[85vh] overflow-y-auto">
            <h3 class="text-lg font-bold text-gray-900 mb-5">{{ addrDialogTitle }}</h3>

            <!-- 表单 -->
            <div class="space-y-4">
              <!-- 收货人 + 电话 -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">收货人 <span class="text-red-400">*</span></label>
                  <input v-model="addrForm.name" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="姓名" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">联系电话 <span class="text-red-400">*</span></label>
                  <input v-model="addrForm.phone" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="手机号码" />
                </div>
              </div>

              <!-- 省市区 -->
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">省</label>
                  <input v-model="addrForm.province" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="省/直辖市" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">市</label>
                  <input v-model="addrForm.city" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="城市" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">区</label>
                  <input v-model="addrForm.region" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="区/县" />
                </div>
              </div>

              <!-- 详细地址 -->
              <div>
                <label class="block text-xs font-medium text-gray-500 mb-1.5">详细地址 <span class="text-red-400">*</span></label>
                <input v-model="addrForm.detailAddress" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="街道、门牌号等" />
              </div>

              <!-- 邮编 + 默认 -->
              <div class="flex items-center gap-6">
                <div class="flex-1">
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">邮政编码</label>
                  <input v-model="addrForm.postCode" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" placeholder="选填" />
                </div>
                <label class="flex items-center gap-2 cursor-pointer pt-5 select-none">
                  <input v-model="addrForm.defaultStatus" :true-value="1" :false-value="0" type="checkbox" class="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                  <span class="text-sm text-gray-600">设为默认地址</span>
                </label>
              </div>
            </div>

            <!-- 按钮 -->
            <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-100">
              <button
                class="px-5 py-2.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                @click="addrDialogVisible = false"
              >
                取消
              </button>
              <button
                :disabled="addrSubmitting"
                class="px-5 py-2.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
                @click="handleSaveAddress"
              >
                {{ addrSubmitting ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* ── 弹窗过渡动画 ── */
.dialog-enter-active { transition: all 0.25s ease-out; }
.dialog-leave-active { transition: all 0.15s ease-in; }
.dialog-enter-from,
.dialog-leave-to { opacity: 0; }
.dialog-enter-from > div:last-child,
.dialog-leave-to > div:last-child {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.line-clamp-1 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
