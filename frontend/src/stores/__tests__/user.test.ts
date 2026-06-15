/**
 * 用户 Store 测试
 * 覆盖: 登录/登出动作、Token 处理、菜单/角色默认值
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

// Mock 外部依赖
vi.mock('@/apis/auth', () => ({
  loginApi: vi.fn(),
  logoutApi: vi.fn(),
  getUserInfoApi: vi.fn(),
}))

vi.mock('@/utils/storage', () => {
  let store: Record<string, string> = {}
  return {
    getToken: vi.fn(() => store['admin_token'] || null),
    setToken: vi.fn((v: string) => { store['admin_token'] = v }),
    removeToken: vi.fn(() => { delete store['admin_token'] }),
    getRefreshToken: vi.fn(() => store['admin_refresh_token'] || null),
    setRefreshToken: vi.fn((v: string) => { store['admin_refresh_token'] = v }),
    removeRefreshToken: vi.fn(() => { delete store['admin_refresh_token'] }),
    getUserInfo: vi.fn(() => {
      const raw = store['admin_user_info']
      return raw ? JSON.parse(raw) : null
    }),
    setUserInfo: vi.fn((info: unknown) => { store['admin_user_info'] = JSON.stringify(info) }),
    removeUserInfo: vi.fn(() => { delete store['admin_user_info'] }),
    clearAuth: vi.fn(() => { store = {} }),
  }
})

// JWT payload: { sub: "1", exp: 9999999999 } (far future)
const FUTURE_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', username: 'admin', exp: 9999999999 })) +
  '.signature'

import { loginApi, logoutApi, getUserInfoApi } from '@/apis/auth'
const mockLoginApi = loginApi as ReturnType<typeof vi.fn>
const mockLogoutApi = logoutApi as ReturnType<typeof vi.fn>
const mockGetUserInfoApi = getUserInfoApi as ReturnType<typeof vi.fn>

describe('useUserStore', () => {
  beforeEach(() => {
    // Fresh Pinia per test
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('initial state', () => {
    it('should have empty user info by default', () => {
      const store = useUserStore()
      expect(store.userInfo.username).toBe('')
      expect(store.userInfo.nickname).toBe('')
      expect(store.userInfo.avatar).toBe('')
      expect(store.userInfo.token).toBe('')
      expect(store.userInfo.menus).toEqual([])
      expect(store.userInfo.roles).toEqual([])
    })

    it('should report not logged in when no token stored', () => {
      const store = useUserStore()
      expect(store.isLoggedIn).toBe(false)
    })

    it('should compute username from userInfo', () => {
      const store = useUserStore()
      expect(store.username).toBe('')
      store.userInfo.username = 'testuser'
      expect(store.username).toBe('testuser')
    })

    it('should compute avatar from userInfo', () => {
      const store = useUserStore()
      expect(store.avatar).toBe('')
      store.userInfo.avatar = 'https://example.com/avatar.png'
      expect(store.avatar).toBe('https://example.com/avatar.png')
    })
  })

  describe('login', () => {
    it('should set token and user info on successful login', async () => {
      const store = useUserStore()

      mockLoginApi.mockResolvedValueOnce({
        data: {
          accessToken: FUTURE_TOKEN,
          refreshToken: 'refresh-token-123',
        },
      })

      mockGetUserInfoApi.mockResolvedValueOnce({
        data: {
          email: 'admin@snaptrip.com',
          nickname: 'Admin',
          avatarUrl: 'https://cdn.snaptrip.com/avatar.png',
        },
      })

      const result = await store.login({ username: 'admin', password: '123456' })

      // Token 已写入
      expect(result.token).toBe(FUTURE_TOKEN)

      // 用户信息已填充
      expect(store.userInfo.username).toBe('admin@snaptrip.com')
      expect(store.userInfo.nickname).toBe('Admin')
      expect(store.userInfo.avatar).toBe('https://cdn.snaptrip.com/avatar.png')

      // 默认菜单和角色已设置
      expect(store.userInfo.menus.length).toBeGreaterThan(0)
      expect(store.userInfo.roles).toContain('admin')

      // 登录后 isLoggedIn 为 true
      expect(store.isLoggedIn).toBe(true)
    })

    it('should fallback to form username when /me API fails', async () => {
      const store = useUserStore()

      mockLoginApi.mockResolvedValueOnce({
        data: {
          accessToken: FUTURE_TOKEN,
          refreshToken: 'refresh-token-456',
        },
      })

      mockGetUserInfoApi.mockRejectedValueOnce(new Error('Network Error'))

      await store.login({ username: 'admin', password: '123456' })

      // 应回退到表单用户名
      expect(store.userInfo.username).toBe('admin')
      expect(store.userInfo.nickname).toBe('admin')
      expect(store.userInfo.avatar).toBe('')
    })
  })

  describe('logout', () => {
    it('should clear user info and call logout API', async () => {
      const store = useUserStore()

      // 先模拟登录后的状态
      mockLoginApi.mockResolvedValueOnce({
        data: {
          accessToken: FUTURE_TOKEN,
          refreshToken: 'refresh-token-789',
        },
      })

      mockGetUserInfoApi.mockResolvedValueOnce({
        data: {
          email: 'admin@snaptrip.com',
          nickname: 'Admin',
          avatarUrl: 'https://cdn.snaptrip.com/avatar.png',
        },
      })

      await store.login({ username: 'admin', password: '123456' })

      // 验证已登录
      expect(store.username).toBe('admin@snaptrip.com')

      // 登出
      mockLogoutApi.mockResolvedValueOnce({ data: {} })
      await store.logout()

      // 验证状态已清除
      expect(store.userInfo.username).toBe('')
      expect(store.userInfo.nickname).toBe('')
      expect(store.userInfo.avatar).toBe('')
      expect(store.userInfo.token).toBe('')
      expect(store.userInfo.menus).toEqual([])
      expect(store.userInfo.roles).toEqual([])
    })

    it('should clear local state even when logout API fails', async () => {
      const store = useUserStore()

      // 设置一个有状态的存储（直接操作 userInfo）
      store.userInfo.username = 'admin@snaptrip.com'
      store.userInfo.nickname = 'Admin'
      store.userInfo.token = FUTURE_TOKEN

      mockLogoutApi.mockRejectedValueOnce(new Error('Server Error'))
      await store.logout()

      // 即使 API 失败，本地状态也应清除
      expect(store.userInfo.username).toBe('')
      expect(store.userInfo.token).toBe('')
    })
  })

  describe('token handling', () => {
    it('should recognize valid token as logged in', async () => {
      const store = useUserStore()

      mockLoginApi.mockResolvedValueOnce({
        data: {
          accessToken: FUTURE_TOKEN,
          refreshToken: 'refresh-token',
        },
      })

      mockGetUserInfoApi.mockResolvedValueOnce({
        data: { email: 'admin@snaptrip.com', nickname: null, avatarUrl: null },
      })

      await store.login({ username: 'admin', password: '123456' })
      expect(store.isLoggedIn).toBe(true)
    })
  })
})
