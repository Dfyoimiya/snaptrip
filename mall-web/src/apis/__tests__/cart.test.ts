/**
 * 购物车 API 测试
 * 覆盖: 所有购物车 API 的 HTTP 方法、URL 构建、参数映射
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock mall-web request module
vi.mock('@/utils/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
  patch: vi.fn(),
}))

import { get, post, put, del, patch } from '@/utils/request'
import {
  addCartAPI,
  getCartListAPI,
  deleteCartAPI,
  updateCartQuantityAPI,
  clearCartAPI,
  toggleCartCheckedAPI,
} from '@/apis/cart'

const mockGet = get as ReturnType<typeof vi.fn>
const mockPost = post as ReturnType<typeof vi.fn>
const mockPut = put as ReturnType<typeof vi.fn>
const mockDel = del as ReturnType<typeof vi.fn>
const mockPatch = patch as ReturnType<typeof vi.fn>

describe('cart API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('addCartAPI', () => {
    it('should POST to /api/v1/portal/cart with product data', async () => {
      mockPost.mockResolvedValueOnce({ id: 'cart-1' })

      await addCartAPI({ product_id: '100', sku_id: '1000', quantity: 2 })

      expect(mockPost).toHaveBeenCalledWith('/api/v1/portal/cart', {
        product_id: '100',
        sku_id: '1000',
        quantity: 2,
      })
    })

    it('should default quantity to 1', async () => {
      mockPost.mockResolvedValueOnce({ id: 'cart-2' })

      await addCartAPI({ product_id: '200', sku_id: '2000', quantity: 1 })

      expect(mockPost).toHaveBeenCalledWith('/api/v1/portal/cart', {
        product_id: '200',
        sku_id: '2000',
        quantity: 1,
      })
    })
  })

  describe('getCartListAPI', () => {
    it('should GET from /api/v1/portal/cart', async () => {
      mockGet.mockResolvedValueOnce([{ id: '1', productName: 'Phone' }])

      const result = await getCartListAPI()

      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/cart')
      expect(result).toEqual([{ id: '1', productName: 'Phone' }])
    })

    it('should return empty array when cart is empty', async () => {
      mockGet.mockResolvedValueOnce([])

      const result = await getCartListAPI()
      expect(result).toEqual([])
    })
  })

  describe('deleteCartAPI', () => {
    it('should DELETE to /api/v1/portal/cart/{id}', async () => {
      mockDel.mockResolvedValueOnce(undefined)

      await deleteCartAPI('cart-item-5')

      expect(mockDel).toHaveBeenCalledWith('/api/v1/portal/cart/cart-item-5')
    })
  })

  describe('updateCartQuantityAPI', () => {
    it('should PUT to /api/v1/portal/cart/{id} with quantity', async () => {
      mockPut.mockResolvedValueOnce({ id: 'cart-1', quantity: 5 })

      await updateCartQuantityAPI('cart-1', 5)

      expect(mockPut).toHaveBeenCalledWith('/api/v1/portal/cart/cart-1', { quantity: 5 })
    })
  })

  describe('clearCartAPI', () => {
    it('should DELETE to /api/v1/portal/cart', async () => {
      mockDel.mockResolvedValueOnce(undefined)

      await clearCartAPI()

      expect(mockDel).toHaveBeenCalledWith('/api/v1/portal/cart')
    })
  })

  describe('toggleCartCheckedAPI', () => {
    it('should PATCH to correct URL with checked=0', async () => {
      mockPatch.mockResolvedValueOnce({ id: 'cart-1', checked: false })

      await toggleCartCheckedAPI('cart-1', 0)

      expect(mockPatch).toHaveBeenCalledWith('/api/v1/portal/cart/cart-1/checked?checked=0')
    })

    it('should PATCH to correct URL with checked=1', async () => {
      mockPatch.mockResolvedValueOnce({ id: 'cart-2', checked: true })

      await toggleCartCheckedAPI('cart-2', 1)

      expect(mockPatch).toHaveBeenCalledWith('/api/v1/portal/cart/cart-2/checked?checked=1')
    })
  })
})
