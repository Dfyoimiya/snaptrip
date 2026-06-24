import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/request', () => ({
  get: vi.fn(),
}))

import { searchProductListAPI } from '@/apis/product'
import { get } from '@/utils/request'

const mockGet = vi.mocked(get)

describe('searchProductListAPI', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockGet.mockResolvedValue({
      page: 1,
      pageSize: 20,
      totalPages: 0,
      total: 0,
      items: [],
    })
  })

  it('uses contains mode and preserves the submitted keyword', async () => {
    await searchProductListAPI({
      keyword: '积木',
      sort: 0,
      page: 1,
      pageSize: 20,
    })

    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/portal/products',
      expect.objectContaining({
        keyword: '积木',
        match_mode: 'contains',
        page: 1,
        page_size: 20,
      }),
    )
  })
})
