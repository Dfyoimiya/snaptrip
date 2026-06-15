/**
 * 购物车 Store 测试
 * 覆盖: 购物车增删改查、选中状态、计算属性、持久化
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import { useCartStore } from '@/stores/cart'
import type { CartItem } from '@/types/cart'

// Mock 购物车 API
vi.mock('@/apis/cart', () => ({
  getCartListAPI: vi.fn(),
  addCartAPI: vi.fn(),
  deleteCartAPI: vi.fn(),
  updateCartQuantityAPI: vi.fn(),
  clearCartAPI: vi.fn(),
  toggleCartCheckedAPI: vi.fn(),
}))

import {
  getCartListAPI,
  addCartAPI,
  deleteCartAPI,
  updateCartQuantityAPI,
  clearCartAPI,
  toggleCartCheckedAPI,
} from '@/apis/cart'

// 工厂函数：创建测试用 CartItem
function makeCartItem(overrides: Partial<CartItem> = {}): CartItem {
  return {
    id: 'cart-1',
    memberId: 'mem-1',
    memberNickname: 'TestUser',
    productId: 100,
    productSkuId: 1000,
    productSkuCode: 'SKU-001',
    productCategoryId: 5,
    productName: 'Test Product',
    productSubTitle: 'A test product',
    productBrand: 'TestBrand',
    productPic: '/img/test.png',
    price: 99,
    originalPrice: 129,
    quantity: 2,
    productAttr: '{}',
    productSn: 'SN-001',
    createDate: '2025-01-01',
    modifyDate: '2025-01-01',
    deleteStatus: 0,
    checked: false,
    ...overrides,
  }
}

describe('useCartStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty cart by default', () => {
      const store = useCartStore()
      expect(store.cartList).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.totalCount).toBe(0)
      expect(store.checkedCount).toBe(0)
      expect(store.checkedTotalPrice).toBe(0)
      expect(store.hasItems).toBe(false)
      expect(store.hasChecked).toBe(false)
      expect(store.isAllChecked).toBe(false)
    })

    it('should restore persisted cart from localStorage', () => {
      const items: CartItem[] = [
        makeCartItem({ id: 'p-1', productName: 'Phone', price: 999, quantity: 1 }),
        makeCartItem({ id: 'p-2', productName: 'Case', price: 49, quantity: 2 }),
      ]
      localStorage.setItem('snaptrip_cart', JSON.stringify(items))

      setActivePinia(createPinia())
      const store = useCartStore()

      expect(store.cartList).toHaveLength(2)
      expect(store.cartList[0].productName).toBe('Phone')
      expect(store.totalCount).toBe(3) // 1 + 2
    })
  })

  describe('computed properties', () => {
    it('totalCount should sum all quantities', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', quantity: 3 }),
        makeCartItem({ id: 'b', quantity: 5 }),
      ]
      expect(store.totalCount).toBe(8)
    })

    it('checkedCount should only count checked items', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', quantity: 2, checked: true }),
        makeCartItem({ id: 'b', quantity: 4, checked: false }),
      ]
      expect(store.checkedCount).toBe(2)
    })

    it('checkedTotalPrice should sum price * quantity for checked items', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', price: 100, quantity: 2, checked: true }),
        makeCartItem({ id: 'b', price: 50, quantity: 3, checked: true }),
        makeCartItem({ id: 'c', price: 200, quantity: 1, checked: false }),
      ]
      expect(store.checkedTotalPrice).toBe(100 * 2 + 50 * 3) // 350
    })

    it('checkedDiscount should be difference between original and total price', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({
          id: 'a', price: 80, originalPrice: 100, quantity: 1, checked: true,
        }),
      ]
      expect(store.checkedDiscount).toBe(20)
    })

    it('isAllChecked should be true when all items checked', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: true }),
        makeCartItem({ id: 'b', checked: true }),
      ]
      expect(store.isAllChecked).toBe(true)
    })

    it('isAllChecked should be false when some unchecked', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: true }),
        makeCartItem({ id: 'b', checked: false }),
      ]
      expect(store.isAllChecked).toBe(false)
    })

    it('isAllChecked should be false for empty cart', () => {
      const store = useCartStore()
      store.cartList = []
      expect(store.isAllChecked).toBe(false)
    })

    it('hasItems should reflect cart emptiness', () => {
      const store = useCartStore()
      expect(store.hasItems).toBe(false)
      store.cartList = [makeCartItem()]
      expect(store.hasItems).toBe(true)
    })

    it('hasChecked should reflect whether any item is checked', () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: false }),
      ]
      expect(store.hasChecked).toBe(false)
      store.cartList[0].checked = true
      expect(store.hasChecked).toBe(true)
    })
  })

  describe('fetchCartList', () => {
    it('should replace cartList with API response', async () => {
      const apiItems: CartItem[] = [
        makeCartItem({ id: 'api-1', productName: 'From API' }),
      ]
      const mockGetList = getCartListAPI as ReturnType<typeof vi.fn>
      mockGetList.mockResolvedValueOnce(apiItems)

      const store = useCartStore()
      await store.fetchCartList()

      expect(store.cartList).toEqual(apiItems)
      expect(store.loading).toBe(false)
    })

    it('should clear cartList on API failure', async () => {
      const store = useCartStore()
      store.cartList = [makeCartItem()] // Pre-seed

      const mockGetList = getCartListAPI as ReturnType<typeof vi.fn>
      mockGetList.mockRejectedValueOnce(new Error('Network Error'))

      await store.fetchCartList()

      expect(store.cartList).toEqual([])
      expect(store.loading).toBe(false)
    })
  })

  describe('removeItem', () => {
    it('should remove item from cartList and call delete API', async () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', productName: 'Keep' }),
        makeCartItem({ id: 'b', productName: 'Remove' }),
      ]

      const mockDelete = deleteCartAPI as ReturnType<typeof vi.fn>
      mockDelete.mockResolvedValueOnce(undefined)

      await store.removeItem('b')

      expect(store.cartList).toHaveLength(1)
      expect(store.cartList[0].id).toBe('a')
      expect(mockDelete).toHaveBeenCalledWith('b')
    })
  })

  describe('removeChecked', () => {
    it('should remove all checked items', async () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: true }),
        makeCartItem({ id: 'b', checked: false }),
        makeCartItem({ id: 'c', checked: true }),
      ]

      const mockDelete = deleteCartAPI as ReturnType<typeof vi.fn>
      mockDelete.mockResolvedValue(undefined)

      await store.removeChecked()

      expect(store.cartList).toHaveLength(1)
      expect(store.cartList[0].id).toBe('b')
      expect(mockDelete).toHaveBeenCalledTimes(2)
    })
  })

  describe('toggleCheckAll', () => {
    it('should set all items to checked', async () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: false }),
        makeCartItem({ id: 'b', checked: false }),
      ]

      const mockToggle = toggleCartCheckedAPI as ReturnType<typeof vi.fn>
      mockToggle.mockResolvedValue(undefined)

      await store.toggleCheckAll(true)

      expect(store.cartList.every((item) => item.checked)).toBe(true)
    })

    it('should set all items to unchecked', async () => {
      const store = useCartStore()
      store.cartList = [
        makeCartItem({ id: 'a', checked: true }),
        makeCartItem({ id: 'b', checked: true }),
      ]

      const mockToggle = toggleCartCheckedAPI as ReturnType<typeof vi.fn>
      mockToggle.mockResolvedValue(undefined)

      await store.toggleCheckAll(false)

      expect(store.cartList.every((item) => !item.checked)).toBe(true)
    })
  })

  describe('updateQuantity', () => {
    it('should not allow quantity below 1', async () => {
      const store = useCartStore()
      const mockUpdate = updateCartQuantityAPI as ReturnType<typeof vi.fn>

      await store.updateQuantity('a', 0)

      // API should not be called
      expect(mockUpdate).not.toHaveBeenCalled()
    })

    it('should cap quantity at 99', async () => {
      const store = useCartStore()
      const mockUpdate = updateCartQuantityAPI as ReturnType<typeof vi.fn>
      mockUpdate.mockResolvedValue(undefined)

      const mockGetList = getCartListAPI as ReturnType<typeof vi.fn>
      const items = [makeCartItem({ id: 'a', quantity: 99 })]
      store.cartList = items
      mockGetList.mockResolvedValueOnce(items)

      await store.updateQuantity('a', 999)

      expect(mockUpdate).toHaveBeenCalledWith('a', 99)
    })
  })

  describe('clearCart', () => {
    it('should call clear API and empty cartList', async () => {
      const store = useCartStore()
      store.cartList = [makeCartItem(), makeCartItem()]

      const mockClear = clearCartAPI as ReturnType<typeof vi.fn>
      mockClear.mockResolvedValueOnce(undefined)

      await store.clearCart()

      expect(store.cartList).toEqual([])
      expect(mockClear).toHaveBeenCalled()
    })
  })

  describe('persistence', () => {
    it('should auto-persist cart to localStorage on changes', async () => {
      const store = useCartStore()
      const item = makeCartItem({ id: 'save-me', productName: 'Saved' })
      store.cartList = [item]

      // 等待 Vue 响应式 watch 异步刷新
      await nextTick()

      const raw = localStorage.getItem('snaptrip_cart')
      expect(raw).not.toBeNull()
      const parsed = JSON.parse(raw!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].productName).toBe('Saved')
    })
  })
})
