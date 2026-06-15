/**
 * ============================================
 * 购物车状态管理 (Pinia Store)
 * ============================================
 */

import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { CartItem } from '@/types/cart'
import {
  getCartListAPI,
  addCartAPI,
  deleteCartAPI,
  updateCartQuantityAPI,
  clearCartAPI,
  toggleCartCheckedAPI,
} from '@/apis/cart'

const STORAGE_KEY = 'snaptrip_cart'

function loadCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

export const useCartStore = defineStore('cart', () => {
  const cartList = ref<CartItem[]>(loadCart())
  const loading = ref(false)

  // Auto-persist
  watch(cartList, (val) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(val)) } catch { /* ignore */ }
  }, { deep: true })

  const totalCount = computed(() =>
    cartList.value.reduce((sum, item) => sum + item.quantity, 0),
  )
  const checkedCount = computed(() =>
    cartList.value.filter((item) => item.checked).reduce((sum, item) => sum + item.quantity, 0),
  )
  const checkedTotalPrice = computed(() =>
    cartList.value.filter((item) => item.checked).reduce((sum, item) => sum + item.price * item.quantity, 0),
  )
  const checkedOriginalPrice = computed(() =>
    cartList.value.filter((item) => item.checked)
      .reduce((sum, item) => sum + (item.originalPrice || item.price) * item.quantity, 0),
  )
  const checkedDiscount = computed(() => checkedOriginalPrice.value - checkedTotalPrice.value)
  const isAllChecked = computed(
    () => cartList.value.length > 0 && cartList.value.every((item) => item.checked),
  )
  const hasItems = computed(() => cartList.value.length > 0)
  const hasChecked = computed(() => cartList.value.some((item) => item.checked))

  const fetchCartList = async () => {
    loading.value = true
    try {
      cartList.value = await getCartListAPI()
    } catch {
      cartList.value = []
    } finally {
      loading.value = false
    }
  }

  const addToCart = async (productId: string, skuId: string, quantity = 1) => {
    await addCartAPI({ product_id: productId, sku_id: skuId, quantity })
    await fetchCartList()
  }

  const updateQuantity = async (id: string, quantity: number) => {
    if (quantity < 1) return
    await updateCartQuantityAPI(id, Math.min(quantity, 99))
    await fetchCartList()
  }

  const removeItem = async (id: string) => {
    await deleteCartAPI(id)
    cartList.value = cartList.value.filter((item) => item.id !== id)
  }

  const removeChecked = async () => {
    const checkedIds = cartList.value.filter((item) => item.checked).map((item) => item.id)
    for (const id of checkedIds) {
      await deleteCartAPI(id)
    }
    cartList.value = cartList.value.filter((item) => !item.checked)
  }

  const toggleCheck = async (id: string) => {
    const item = cartList.value.find((i) => i.id === id)
    if (!item) return
    const newChecked = item.checked ? 0 : 1
    await toggleCartCheckedAPI(id, newChecked)
    item.checked = !item.checked
  }

  const toggleCheckAll = async (checked: boolean) => {
    for (const item of cartList.value) {
      if (!!item.checked !== checked) {
        await toggleCartCheckedAPI(item.id, checked ? 1 : 0)
      }
    }
    cartList.value.forEach((item) => { item.checked = checked })
  }

  const clearCart = async () => {
    await clearCartAPI()
    cartList.value = []
  }

  return {
    cartList, loading,
    totalCount, checkedCount, checkedTotalPrice, checkedOriginalPrice, checkedDiscount,
    isAllChecked, hasItems, hasChecked,
    fetchCartList, addToCart, updateQuantity, removeItem, removeChecked,
    toggleCheck, toggleCheckAll, clearCart,
  }
})
