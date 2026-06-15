/**
 * Token 刷新模块测试
 * 覆盖: refreshAccessToken 单例 Promise 共享、isRefreshing 状态管理、
 *       成功刷新后 token 持久化、无 refresh token 时报错
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

// ─── Mock storage ──────────────────────────────────────────────
const storageState: Record<string, string> = {}
vi.mock('@/utils/storage', () => ({
  getToken: vi.fn(() => storageState['admin_token'] || null),
  setToken: vi.fn((v: string) => { storageState['admin_token'] = v }),
  getRefreshToken: vi.fn(() => storageState['admin_refresh_token'] || null),
  setRefreshToken: vi.fn((v: string) => { storageState['admin_refresh_token'] = v }),
  clearAuth: vi.fn(() => {
    delete storageState['admin_token']
    delete storageState['admin_refresh_token']
    delete storageState['admin_user_info']
  }),
}))

// ─── Mock axios for the raw refresh call ───────────────────────
const mockAxiosPost = vi.fn()
vi.mock('axios', () => ({
  default: {
    post: (...args: any[]) => mockAxiosPost(...args),
  },
}))

// ─── Now import the module under test ──────────────────────────
import { refreshAccessToken, isRefreshing } from '@/utils/tokenRefresh'
import { setToken, setRefreshToken, clearAuth } from '@/utils/storage'

describe('tokenRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear the module-level state (the singleton Promise)
    Object.keys(storageState).forEach((k) => delete storageState[k])
    // Force reset the module's internal refreshPromise by re-importing
    // ...but that's not possible with static imports. We rely on the
    // .finally() callback which clears the Promise after resolution.
  })

  describe('refreshAccessToken', () => {
    it('should call refresh endpoint with stored refresh token', async () => {
      storageState['admin_refresh_token'] = 'rt-abc'

      mockAxiosPost.mockResolvedValueOnce({
        data: {
          code: 0,
          data: {
            access_token: 'new-access',
            refresh_token: 'new-refresh',
          },
        },
      })

      const token = await refreshAccessToken()

      expect(mockAxiosPost).toHaveBeenCalledWith(
        expect.stringContaining('/auth/refresh'),
        { refresh_token: 'rt-abc' },
        { timeout: 10000 },
      )
      expect(token).toBe('new-access')
    })

    it('should persist new tokens on success', async () => {
      storageState['admin_refresh_token'] = 'rt-def'

      mockAxiosPost.mockResolvedValueOnce({
        data: {
          code: 0,
          data: {
            access_token: 'fresh-access',
            refresh_token: 'fresh-refresh',
          },
        },
      })

      await refreshAccessToken()

      // setToken and setRefreshToken should have been called
      expect(storageState['admin_token']).toBe('fresh-access')
    })

    it('should throw when no refresh token is stored', async () => {
      // Ensure no refresh token in storage
      delete storageState['admin_refresh_token']

      await expect(refreshAccessToken()).rejects.toThrow('No refresh token')
    })

    it('should throw when API returns non-zero code', async () => {
      storageState['admin_refresh_token'] = 'rt-bad'

      mockAxiosPost.mockResolvedValueOnce({
        data: {
          code: 401,
          message: 'Refresh token expired',
          data: null,
        },
      })

      await expect(refreshAccessToken()).rejects.toThrow('Refresh token expired')
    })

    it('should clear auth on refresh failure', async () => {
      storageState['admin_refresh_token'] = 'rt-will-fail'

      mockAxiosPost.mockRejectedValueOnce(new Error('Network Error'))

      await expect(refreshAccessToken()).rejects.toThrow()

      // clearAuth should have been called
      const { clearAuth: mockClearAuth } = await import('@/utils/storage')
      expect(mockClearAuth).toHaveBeenCalled()
    })

    it('should share the same Promise for concurrent calls', async () => {
      storageState['admin_refresh_token'] = 'rt-concurrent'

      let resolveRefresh!: (value: any) => void
      const refreshDeferred = new Promise<any>((resolve) => {
        resolveRefresh = resolve
      })
      mockAxiosPost.mockReturnValueOnce(refreshDeferred)

      // Start refresh — returns singleton Promise
      const promise1 = refreshAccessToken()
      expect(isRefreshing()).toBe(true)

      // Concurrent call should return the same Promise
      const promise2 = refreshAccessToken()

      // Resolve the deferred
      resolveRefresh({
        data: {
          code: 0,
          data: { access_token: 'shared-token', refresh_token: 'shared-rt' },
        },
      })

      const [result1, result2] = await Promise.all([promise1, promise2])
      expect(result1).toBe('shared-token')
      expect(result2).toBe('shared-token')

      // After resolution, isRefreshing should be false
      expect(isRefreshing()).toBe(false)
    })
  })

  describe('isRefreshing', () => {
    it('should return false when no refresh is in progress', () => {
      expect(isRefreshing()).toBe(false)
    })

    it('should return true during a refresh', async () => {
      storageState['admin_refresh_token'] = 'rt-isref'

      let resolveRefresh!: (value: any) => void
      mockAxiosPost.mockReturnValueOnce(
        new Promise((resolve) => { resolveRefresh = resolve }),
      )

      const promise = refreshAccessToken()
      expect(isRefreshing()).toBe(true)

      // Clean up
      resolveRefresh({ data: { code: 0, data: { access_token: 'x', refresh_token: 'y' } } })
      await promise
    })
  })
})
