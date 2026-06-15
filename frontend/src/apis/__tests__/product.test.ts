/**
 * 商品 API 参数映射测试
 * 覆盖: mapProductParams 将 camelCase 前端参数正确映射为 snake_case 后端参数
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock request 模块
vi.mock('@/utils/request', () => ({
  default: vi.fn(),
}))

import {
  getProductListAPI,
  createProductAPI,
  updateProductAPI,
  getProductAPI,
  productUpdateDeleteStatusAPI,
  productUpdateNewStatusAPI,
  productUpdateRecommendStatusAPI,
  productUpdatePublishStatusAPI,
} from '@/apis/product'
import request from '@/utils/request'

const mockRequest = request as ReturnType<typeof vi.fn>

describe('product API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getProductListAPI', () => {
    it('should map ProductQueryParam to snake_case query params', async () => {
      const params = {
        keyword: '手机',
        productSn: 'SN-001',
        categoryId: '5',
        brandId: '10',
        publishStatus: 1,
        verifyStatus: 1,
        page: 1,
        page_size: 10,
      }

      mockRequest.mockResolvedValueOnce({ data: { code: 200, data: { items: [], total: 0 } } })

      await getProductListAPI(params)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('get')
      expect(callArgs.url).toBe('/admin/products')

      // 验证参数映射：camelCase → snake_case
      const mappedParams = callArgs.params
      expect(mappedParams.keyword).toBe('手机')
      expect(mappedParams.product_sn).toBe('SN-001')
      expect(mappedParams.category_id).toBe('5')
      expect(mappedParams.brand_id).toBe('10')
      expect(mappedParams.publish_status).toBe(1)
      expect(mappedParams.verify_status).toBe(1)
      expect(mappedParams.page).toBe(1)
      expect(mappedParams.page_size).toBe(10)
    })

    it('should only map provided fields (omit undefined)', async () => {
      const params = {
        keyword: undefined,
        page: 1,
        page_size: 20,
      }

      mockRequest.mockResolvedValueOnce({ data: { code: 200 } })

      await getProductListAPI(params)

      const mappedParams = mockRequest.mock.calls[0][0].params
      expect(mappedParams.keyword).toBeUndefined()
      expect(mappedParams.page).toBe(1)
      // 未提供的字段不应存在或为 undefined
      expect(mappedParams.brand_id).toBeUndefined()
    })
  })

  describe('createProductAPI', () => {
    it('should POST to /admin/products with product data', async () => {
      const data = {
        name: 'Test Phone',
        brandId: '1',
        categoryId: '10',
        productSn: 'SN-NEW',
        defaultPic: '/img/test.png',
        price: 2999,
        subTitle: 'Best phone',
      }

      mockRequest.mockResolvedValueOnce({ data: { code: 200, data: 1 } })

      await createProductAPI(data)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('post')
      expect(callArgs.url).toBe('/admin/products')
      expect(callArgs.data).toEqual(data)
    })
  })

  describe('updateProductAPI', () => {
    it('should PUT to /admin/products/{id} with product data', async () => {
      const data = { name: 'Updated Phone', price: 2599, brandId: '1', categoryId: '10', defaultPic: '', productSn: '', subTitle: '' }

      mockRequest.mockResolvedValueOnce({ data: { code: 200, data: 1 } })

      await updateProductAPI('42', data)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('put')
      expect(callArgs.url).toBe('/admin/products/42')
      expect(callArgs.data).toEqual(data)
    })
  })

  describe('getProductAPI', () => {
    it('should GET /admin/products/{id}', async () => {
      mockRequest.mockResolvedValueOnce({ data: { code: 200, data: {} } })

      await getProductAPI('99')

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('get')
      expect(callArgs.url).toBe('/admin/products/99')
    })
  })

  describe('productUpdateDeleteStatusAPI', () => {
    it('should DELETE /admin/products/{id}', async () => {
      mockRequest.mockResolvedValueOnce({ data: { code: 200 } })

      await productUpdateDeleteStatusAPI('7')

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('delete')
      expect(callArgs.url).toBe('/admin/products/7')
    })
  })

  describe('productUpdateNewStatusAPI', () => {
    it('should PATCH /admin/products/{id}/new with status param', async () => {
      mockRequest.mockResolvedValueOnce({ data: { code: 200 } })

      await productUpdateNewStatusAPI('12', 1)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('patch')
      expect(callArgs.url).toBe('/admin/products/12/new')
      expect(callArgs.params).toEqual({ status: 1 })
    })
  })

  describe('productUpdateRecommendStatusAPI', () => {
    it('should PATCH /admin/products/{id}/recommend with status param', async () => {
      mockRequest.mockResolvedValueOnce({ data: { code: 200 } })

      await productUpdateRecommendStatusAPI('12', 0)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('patch')
      expect(callArgs.url).toBe('/admin/products/12/recommend')
      expect(callArgs.params).toEqual({ status: 0 })
    })
  })

  describe('productUpdatePublishStatusAPI', () => {
    it('should PATCH /admin/products/{id}/status with status param', async () => {
      mockRequest.mockResolvedValueOnce({ data: { code: 200 } })

      await productUpdatePublishStatusAPI('34', 1)

      const callArgs = mockRequest.mock.calls[0][0]
      expect(callArgs.method).toBe('patch')
      expect(callArgs.url).toBe('/admin/products/34/status')
      expect(callArgs.params).toEqual({ status: 1 })
    })
  })
})
