/**
 * 会员状态管理测试
 * 覆盖: 登录状态持久化、setLoginInfo、memberLogout、计算属性
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import { useMemberStore } from '@/stores/member'

// Mock 外部 API
vi.mock('@/apis/member', () => ({
  logoutAPI: vi.fn(),
}))

import { logoutAPI } from '@/apis/member'
const mockLogoutAPI = logoutAPI as ReturnType<typeof vi.fn>

// Mock localStorage
const STORAGE_KEY = 'snaptrip_member'

describe('useMemberStore', () => {
  beforeEach(() => {
    // Fresh Pinia
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty auth state by default', () => {
      const store = useMemberStore()
      expect(store.token).toBe('')
      expect(store.refreshToken).toBe('')
      expect(store.memberInfo).toBeNull()
      expect(store.isLoggedIn).toBe(false)
      expect(store.displayName).toBe('')
      expect(store.avatar).toBe('')
      expect(store.integration).toBe(0)
    })

    it('should restore persisted state from localStorage', () => {
      const persisted = {
        token: 'persisted-token',
        refreshToken: 'persisted-refresh',
        memberInfo: {
          id: '1',
          email: 'user@example.com',
          nickname: 'TestUser',
          avatarUrl: 'https://cdn.example.com/ava.png',
          integration: 100,
        },
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted))

      // Re-create store to pick up persisted data
      setActivePinia(createPinia())
      const store = useMemberStore()

      expect(store.token).toBe('persisted-token')
      expect(store.refreshToken).toBe('persisted-refresh')
      expect(store.memberInfo?.email).toBe('user@example.com')
      expect(store.isLoggedIn).toBe(true)
      expect(store.displayName).toBe('TestUser')
      expect(store.avatar).toBe('https://cdn.example.com/ava.png')
      expect(store.integration).toBe(100)
    })
  })

  describe('setLoginInfo', () => {
    it('should set token, refreshToken, and memberInfo', () => {
      const store = useMemberStore()

      store.setLoginInfo('access-abc', 'refresh-abc', {
        id: '2',
        email: 'new@example.com',
        nickname: 'NewUser',
        avatarUrl: '/ava2.png',
        integration: 50,
      })

      expect(store.token).toBe('access-abc')
      expect(store.refreshToken).toBe('refresh-abc')
      expect(store.memberInfo?.email).toBe('new@example.com')
      expect(store.isLoggedIn).toBe(true)
    })

    it('should work without optional memberInfo', () => {
      const store = useMemberStore()
      store.setLoginInfo('token-only', 'refresh-only')

      expect(store.token).toBe('token-only')
      expect(store.refreshToken).toBe('refresh-only')
      expect(store.memberInfo).toBeNull() // unchanged
      expect(store.isLoggedIn).toBe(true)
    })
  })

  describe('setMemberInfo', () => {
    it('should update member info independently', () => {
      const store = useMemberStore()

      store.setMemberInfo({
        id: '3',
        email: 'update@example.com',
        nickname: 'Updated',
        avatarUrl: '/ava3.png',
        integration: 200,
      })

      expect(store.memberInfo?.nickname).toBe('Updated')
      expect(store.displayName).toBe('Updated')
      expect(store.integration).toBe(200)
    })
  })

  describe('memberLogout', () => {
    it('should clear all auth state and call logout API', async () => {
      const store = useMemberStore()

      // Set logged-in state
      store.setLoginInfo('access-token', 'refresh-token', {
        id: '1',
        email: 'user@example.com',
        nickname: 'User',
        avatarUrl: '/ava.png',
      })

      mockLogoutAPI.mockResolvedValueOnce(undefined)

      await store.memberLogout()

      expect(store.token).toBe('')
      expect(store.refreshToken).toBe('')
      expect(store.memberInfo).toBeNull()
      expect(store.isLoggedIn).toBe(false)
      expect(store.displayName).toBe('')
      expect(mockLogoutAPI).toHaveBeenCalledWith('refresh-token')
    })

    it('should clear state even when logout API fails', async () => {
      const store = useMemberStore()

      store.setLoginInfo('bad-token', 'bad-refresh', {
        id: '1',
        email: 'fail@example.com',
        nickname: 'FailUser',
        avatarUrl: '',
      })

      mockLogoutAPI.mockRejectedValueOnce(new Error('Network Error'))

      await store.memberLogout()

      expect(store.token).toBe('')
      expect(store.isLoggedIn).toBe(false)
    })
  })

  describe('computed properties', () => {
    it('displayName should fallback to email when no nickname', () => {
      const store = useMemberStore()
      store.setMemberInfo({
        id: '4',
        email: 'nonick@example.com',
        nickname: '',
        avatarUrl: '',
      })
      expect(store.displayName).toBe('nonick@example.com')
    })

    it('avatar should be empty string when memberInfo is null', () => {
      const store = useMemberStore()
      expect(store.avatar).toBe('')
    })

    it('integration should default to 0 when undefined', () => {
      const store = useMemberStore()
      store.setMemberInfo({
        id: '5',
        email: 'nointeg@example.com',
        nickname: 'NoInteg',
        avatarUrl: '',
      })
      expect(store.integration).toBe(0)
    })
  })

  describe('persistence', () => {
    it('should auto-persist auth state to localStorage', async () => {
      const store = useMemberStore()

      store.setLoginInfo('token-persist', 'refresh-persist', {
        id: '6',
        email: 'persist@example.com',
        nickname: 'Persist',
        avatarUrl: '/p.png',
      })

      // 等待 Vue 响应式 watch 异步刷新
      await nextTick()

      const raw = localStorage.getItem(STORAGE_KEY)
      expect(raw).not.toBeNull()
      const parsed = JSON.parse(raw!)
      expect(parsed.token).toBe('token-persist')
      expect(parsed.memberInfo.email).toBe('persist@example.com')
    })
  })
})
