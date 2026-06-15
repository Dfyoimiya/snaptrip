/**
 * 共享 Token 刷新模块 —— 单例控制并发刷新。
 *
 * 问题: 路由守卫 (guard.ts) 和 axios 拦截器 (request.ts) 各自独立刷新 token，
 * 使用不同的 isRefreshing 标志，并发时可能发起两次刷新请求导致 token 错乱。
 *
 * 解决: 模块级单例 Promise + 等待队列。无论谁先触发刷新，后续调用者都复用
 * 同一个 Promise，确保全局只有一条刷新请求在飞。
 */
import axios from 'axios'
import { getRefreshToken, setToken, setRefreshToken, clearAuth } from './storage'

/** 模块级刷新控制 —— 全局唯一 */
let refreshPromise: Promise<string> | null = null

/** 执行实际的 token 刷新请求（不依赖 axios 实例，避免拦截器死循环） */
function doRefresh(): Promise<string> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return Promise.reject(new Error('No refresh token available'))
  }

  return axios
    .post(
      `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 10000 },
    )
    .then((response) => {
      const res = response.data
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || 'Token refresh failed')
      }
      const { access_token, refresh_token } = res.data
      setToken(access_token)
      setRefreshToken(refresh_token)
      return access_token
    })
    .catch((error) => {
      clearAuth()
      throw error
    })
}

/**
 * 获取有效的 access token。
 *
 * 如果已有刷新在进行中，返回该 Promise（共享调用）。
 * 如果没有，发起新刷新并缓存 Promise。
 * 刷新完成（成功或失败）后清除缓存，允许后续调用重新触发。
 */
export function refreshAccessToken(): Promise<string> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = doRefresh().finally(() => {
    refreshPromise = null
  })

  return refreshPromise
}

/**
 * 是否有刷新正在进行中。
 * 用于调用方判断是否需要将请求加入等待队列。
 */
export function isRefreshing(): boolean {
  return refreshPromise !== null
}
