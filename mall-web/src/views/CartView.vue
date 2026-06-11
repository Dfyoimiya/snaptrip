<script setup lang="ts">
/**
 * ============================================
 * 购物车页面 (CartView)
 * PC 端标准宽屏表格布局
 * - 表头：全选 / 商品信息 / 单价 / 数量 / 小计 / 操作
 * - 全选/反选联动，数量增减实时计算
 * - 底部固定悬浮结算栏 + 大高亮去结算按钮
 * - 所有计算逻辑在前端实时响应，不依赖后端
 * ============================================
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import type { CartItem } from '@/types/cart'

const router = useRouter()
const cartStore = useCartStore()

/** 加载状态 */
const loading = ref(false)
/** 显示删除确认 */
const showDeleteConfirm = ref(false)
/** 待删除项 ID */
const pendingDeleteId = ref('')

// ===== 核心计算逻辑（前端实时响应） =====

/**
 * 计算单个商品小计
 */
const calcSubtotal = (item: CartItem): number => {
  return item.price * item.quantity
}

/**
 * 格式化价格（千分位 + 两位小数）
 */
const formatPrice = (price: number): string => {
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ===== 交互操作 =====

/**
 * 初始化购物车数据
 */
const initCart = async () => {
  loading.value = true
  try {
    await cartStore.fetchCartList()
  } finally {
    loading.value = false
  }
}

/**
 * 减少数量
 */
const handleDecrease = (item: CartItem) => {
  if (item.quantity <= 1) return
  cartStore.updateQuantity(item.id, item.quantity - 1)
}

/**
 * 增加数量
 */
const handleIncrease = (item: CartItem) => {
  if (item.quantity >= 99) return
  cartStore.updateQuantity(item.id, item.quantity + 1)
}

/**
 * 直接输入数量
 */
const handleInputQuantity = (item: CartItem, e: Event) => {
  const input = e.target as HTMLInputElement
  let val = parseInt(input.value)
  if (isNaN(val) || val < 1) val = 1
  if (val > 99) val = 99
  cartStore.updateQuantity(item.id, val)
  input.value = String(val)
}

/**
 * 请求删除（显示确认）
 */
const requestDelete = (id: string) => {
  pendingDeleteId.value = id
  showDeleteConfirm.value = true
}

/**
 * 确认删除
 */
const confirmDelete = () => {
  if (pendingDeleteId.value) {
    cartStore.removeItem(pendingDeleteId.value)
  }
  showDeleteConfirm.value = false
  pendingDeleteId.value = ''
}

/**
 * 取消删除
 */
const cancelDelete = () => {
  showDeleteConfirm.value = false
  pendingDeleteId.value = ''
}

/**
 * 删除选中商品
 */
const handleDeleteChecked = () => {
  cartStore.removeChecked()
}

/**
 * 清空购物车
 */
const handleClearAll = () => {
  if (confirm('确定要清空购物车吗？')) {
    cartStore.clearCart()
  }
}

/**
 * 去结算
 */
const handleCheckout = () => {
  if (!cartStore.hasChecked) return
  const checkedIds = cartStore.cartList
    .filter((item) => item.checked)
    .map((item) => Number(item.id))
  router.push({
    path: '/order-confirm',
    query: { cartIds: checkedIds.join(',') },
  })
}

/**
 * 跳转到商品详情
 */
const goProductDetail = (productId: number) => {
  router.push(`/product/${productId}`)
}

onMounted(() => {
  initCart()
})
</script>

<template>
  <div class="cart-page">
    <!-- ===== 页面标题区 ===== -->
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold text-gray-900">
        购物车
        <span class="text-sm font-normal text-gray-400 ml-2">
          共 {{ cartStore.totalCount }} 件商品
        </span>
      </h1>
      <button
        v-if="cartStore.hasItems"
        class="text-sm text-gray-400 hover:text-red-600 transition-colors"
        @click="handleClearAll"
      >
        清空购物车
      </button>
    </div>

    <!-- ===== 加载中 ===== -->
    <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-100 py-24">
      <div class="flex flex-col items-center gap-3 text-gray-400">
        <svg class="animate-spin h-8 w-8" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span class="text-sm">购物车加载中...</span>
      </div>
    </div>

    <!-- ===== 空购物车 ===== -->
    <div
      v-else-if="!cartStore.hasItems"
      class="bg-white rounded-xl shadow-sm border border-gray-100 py-24"
    >
      <div class="flex flex-col items-center text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-20 w-20 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <p class="text-lg text-gray-500 mb-2">购物车还是空的</p>
        <p class="text-sm text-gray-400 mb-6">快去挑选心仪的商品吧</p>
        <button
          class="px-8 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
          @click="router.push('/')">
          去逛逛
        </button>
      </div>
    </div>

    <!-- ===== 购物车主体（表格形式） ===== -->
    <template v-else>
      <!-- 表格头部 -->
      <div class="bg-white rounded-t-xl shadow-sm border border-gray-100 border-b-0">
        <div class="grid grid-cols-[48px_1fr_140px_160px_140px_100px] items-center px-6 py-3.5 bg-gray-50 text-sm text-gray-500 rounded-t-xl">
          <!-- 全选 -->
          <div class="flex items-center">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                :checked="cartStore.isAllChecked"
                class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer"
                @change="cartStore.toggleCheckAll(($event.target as HTMLInputElement).checked)"
              />
              <span class="text-xs">全选</span>
            </label>
          </div>
          <!-- 商品信息 -->
          <div class="pl-2">商品信息</div>
          <!-- 单价 -->
          <div class="text-center">单价</div>
          <!-- 数量 -->
          <div class="text-center">数量</div>
          <!-- 小计 -->
          <div class="text-center">小计</div>
          <!-- 操作 -->
          <div class="text-center">操作</div>
        </div>
      </div>

      <!-- 商品列表 -->
      <div class="bg-white shadow-sm border-x border-gray-100 divide-y divide-gray-50">
        <div
          v-for="item in cartStore.cartList"
          :key="item.id"
          class="grid grid-cols-[48px_1fr_140px_160px_140px_100px] items-center px-6 py-5 hover:bg-red-50/30 transition-colors group"
        >
          <!-- 复选框 -->
          <div class="flex items-center">
            <input
              type="checkbox"
              :checked="item.checked"
              class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer"
              @change="cartStore.toggleCheck(item.id)"
            />
          </div>

          <!-- 商品信息 -->
          <div class="flex items-center gap-4 pl-2 min-w-0">
            <!-- 商品图片 -->
            <button
              class="w-20 h-20 rounded-lg bg-gray-50 flex-shrink-0 overflow-hidden border border-gray-100 hover:border-red-200 transition-colors"
              @click="goProductDetail(item.productId)"
            >
              <img
                :src="item.productPic"
                :alt="item.productName"
                class="w-full h-full object-cover"
              />
            </button>
            <!-- 商品名称和规格 -->
            <div class="min-w-0 flex-1">
              <button
                class="text-sm text-gray-800 font-medium line-clamp-2 text-left hover:text-red-600 transition-colors leading-5"
                @click="goProductDetail(item.productId)"
              >
                {{ item.productName }}
              </button>
              <p class="text-xs text-gray-400 mt-1.5 truncate">
                {{ item.spDataStr || item.productSkuCode }}
              </p>
            </div>
          </div>

          <!-- 单价 -->
          <div class="text-center">
            <div class="text-sm text-gray-900 font-medium">
              &yen;{{ formatPrice(item.price) }}
            </div>
            <div v-if="item.originalPrice && item.originalPrice > item.price" class="text-xs text-gray-400 line-through mt-0.5">
              &yen;{{ formatPrice(item.originalPrice) }}
            </div>
          </div>

          <!-- 数量控件 -->
          <div class="flex items-center justify-center">
            <div class="flex items-center border border-gray-200 rounded-md overflow-hidden group-hover:border-gray-300 transition-colors">
              <!-- 减号 -->
              <button
                class="w-9 h-9 flex items-center justify-center bg-white text-gray-500 hover:bg-gray-50 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="item.quantity <= 1"
                @click="handleDecrease(item)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4" />
                </svg>
              </button>
              <!-- 数量输入 -->
              <input
                :value="item.quantity"
                type="text"
                class="w-12 h-9 text-center text-sm text-gray-900 border-x border-gray-200 focus:outline-none focus:ring-0 bg-white"
                @blur="handleInputQuantity(item, $event)"
                @keydown.enter="handleInputQuantity(item, $event)"
              />
              <!-- 加号 -->
              <button
                class="w-9 h-9 flex items-center justify-center bg-white text-gray-500 hover:bg-gray-50 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="item.quantity >= 99"
                @click="handleIncrease(item)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 小计（实时计算） -->
          <div class="text-center">
            <div class="text-base font-bold text-red-600">
              &yen;{{ formatPrice(calcSubtotal(item)) }}
            </div>
          </div>

          <!-- 操作 -->
          <div class="flex items-center justify-center">
            <button
              class="text-sm text-gray-400 hover:text-red-600 px-3 py-1 rounded hover:bg-red-50 transition-colors"
              @click="requestDelete(item.id)"
            >
              删除
            </button>
          </div>
        </div>
      </div>

      <!-- ===== 底部结算栏（固定悬浮） ===== -->
      <div
        class="sticky bottom-0 z-30 mt-0 bg-white border border-gray-100 rounded-b-xl shadow-lg shadow-gray-200/50"
      >
        <div class="flex items-center justify-between px-6 py-4">
          <!-- 左侧操作 -->
          <div class="flex items-center gap-6 text-sm">
            <!-- 全选 -->
            <label class="flex items-center gap-2 cursor-pointer select-none text-gray-600">
              <input
                type="checkbox"
                :checked="cartStore.isAllChecked"
                class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer"
                @change="cartStore.toggleCheckAll(($event.target as HTMLInputElement).checked)"
              />
              <span>全选</span>
            </label>

            <!-- 删除选中 -->
            <button
              class="text-gray-500 hover:text-red-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              :disabled="!cartStore.hasChecked"
              @click="handleDeleteChecked"
            >
              删除选中
            </button>

            <!-- 已选数量 -->
            <span class="text-gray-500">
              已选 <span class="text-red-600 font-medium">{{ cartStore.checkedCount }}</span> 件商品
            </span>
          </div>

          <!-- 右侧结算 -->
          <div class="flex items-center gap-6">
            <!-- 价格汇总 -->
            <div class="text-right">
              <!-- 优惠金额 -->
              <div v-if="cartStore.checkedDiscount > 0" class="text-xs text-gray-400 mb-1">
                已优惠 &yen;{{ formatPrice(cartStore.checkedDiscount) }}
              </div>
              <!-- 总价 -->
              <div class="flex items-baseline gap-2">
                <span class="text-sm text-gray-600">合计：</span>
                <span class="text-2xl font-bold text-red-600">
                  <span class="text-sm">&yen;</span>{{ formatPrice(cartStore.checkedTotalPrice) }}
                </span>
              </div>
            </div>

            <!-- 去结算按钮（大高亮） -->
            <button
              :disabled="!cartStore.hasChecked"
              class="relative h-14 px-10 bg-red-600 text-white text-lg font-bold rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all shadow-lg shadow-red-200 hover:shadow-xl hover:shadow-red-300 active:scale-[0.98]"
              @click="handleCheckout"
            >
              去结算
              <span
                v-if="cartStore.checkedCount > 0"
                class="absolute -top-2 -right-2 min-w-5 h-5 bg-orange-500 text-white text-xs rounded-full flex items-center justify-center px-1 shadow-sm"
              >
                {{ cartStore.checkedCount }}
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- 底部提示 -->
      <div class="text-center text-xs text-gray-400 mt-4 pb-4">
        正品保障 · 7天无理由退换 · 全国联保 · 极速发货
      </div>
    </template>

    <!-- ===== 删除确认弹窗 ===== -->
    <Teleport to="body">
      <div
        v-if="showDeleteConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        @click.self="cancelDelete"
      >
        <div class="bg-white rounded-xl shadow-2xl p-6 w-96 mx-4 animate-[fadeIn_0.2s_ease-out]">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <div>
              <h3 class="text-base font-bold text-gray-900">确认删除</h3>
              <p class="text-sm text-gray-500 mt-0.5">确定要删除该商品吗？</p>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-6">
            <button
              class="flex-1 h-10 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
              @click="cancelDelete"
            >
              取消
            </button>
            <button
              class="flex-1 h-10 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
              @click="confirmDelete"
            >
              确认删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* 行省略 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 淡入动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* 隐藏输入框的增减按钮 */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 表格行 hover 效果过渡 */
.group {
  transition: background-color 0.15s ease;
}
</style>
