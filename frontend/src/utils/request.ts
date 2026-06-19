import axios from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { getToken, getRefreshToken, clearAuth } from './storage'
import { isTokenExpired } from './jwt'
import { refreshAccessToken, isRefreshing } from './tokenRefresh'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
})

// ── Token 刷新队列（防止并发 401 时重复刷新） ──────────────────────────

let pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: any) => void
}> = []

/** 将因 token 过期挂起的请求加入队列，等待刷新完成后重试 */
function addPendingRequest(resolve: (token: string) => void, reject: (error: any) => void) {
  pendingRequests.push({ resolve, reject })
}

/** 刷新成功后，用新 token 重试所有挂起的请求 */
function processPendingRequests(token: string) {
  pendingRequests.forEach(({ resolve }) => resolve(token))
  pendingRequests = []
}

/** 刷新失败后，拒绝所有挂起的请求 */
function rejectPendingRequests(error: any) {
  pendingRequests.forEach(({ reject }) => reject(error))
  pendingRequests = []
}

// ── snake_case → camelCase 深度转换 ────────────────────────────────────────

function snakeToCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())
}

function deepConvertKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(deepConvertKeys)
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[snakeToCamel(key)] = deepConvertKeys(value)
    }
    return result
  }
  return obj
}

// ── 请求拦截器 ──────────────────────────────────────────────────────────

request.interceptors.request.use(
  async (config) => {
    const token = getToken()
    if (token && isTokenExpired(token) && !config.url?.includes('/auth/refresh')) {
      // 如果已经在刷新中，等待当前刷新完成
      if (isRefreshing()) {
        return new Promise((resolve, reject) => {
          addPendingRequest(
            (newToken: string) => {
              config.headers.Authorization = `Bearer ${newToken}`
              resolve(config)
            },
            (err: any) => {
              reject(err)
            },
          )
        })
      }

      try {
        const newToken = await refreshAccessToken()
        processPendingRequests(newToken)
        config.headers.Authorization = `Bearer ${newToken}`
        return config
      } catch {
        rejectPendingRequests(new Error('Token refresh failed'))
        // 刷新失败，仍发送请求（让后端返回 401，由响应拦截器处理跳转）
        return config
      }
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// ── 响应拦截器 ──────────────────────────────────────────────────────────

request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    if (res.code !== 0) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    // 深度转换 snake_case → camelCase
    if (res.data) {
      res.data = deepConvertKeys(res.data)
    }
    return res
  },
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean; _retryCount?: number }

    // 只处理 401 且不是刷新请求本身（避免死循环）
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      const refreshToken = getRefreshToken()

      if (refreshToken) {
        // 如果已经在刷新中，将请求加入等待队列
        if (isRefreshing()) {
          return new Promise((resolve, reject) => {
            addPendingRequest(
              (newToken: string) => {
                originalRequest.headers.Authorization = `Bearer ${newToken}`
                resolve(request(originalRequest))
              },
              (err: any) => {
                reject(err)
              },
            )
          })
        }

        originalRequest._retry = true

        try {
          const newToken = await refreshAccessToken()
          processPendingRequests(newToken)

          // 重试原始请求
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return request(originalRequest)
        } catch (refreshError) {
          rejectPendingRequests(refreshError)

          // 刷新失败，跳转登录
          ElMessage.error('登录已过期，请重新登录')
          // 延迟跳转，避免在并发请求时多次弹窗
          setTimeout(() => {
            const currentPath = window.location.hash.replace('#', '') || '/'
            window.location.href = `#/login?redirect=${encodeURIComponent(currentPath)}`
            window.location.reload()
          }, 100)
          return Promise.reject(refreshError)
        }
      }

      // 没有 refresh token，直接跳转登录
      clearAuth()
      ElMessage.error('登录已过期，请重新登录')
      setTimeout(() => {
        const currentPath = window.location.hash.replace('#', '') || '/'
        window.location.href = `#/login?redirect=${encodeURIComponent(currentPath)}`
        window.location.reload()
      }, 100)
      return Promise.reject(error)
    }

    if (error.response?.status === 403) {
      const message = error.response?.data?.message || error.response?.data?.detail || '暂无访问权限'
      ElMessage.error(message)
      if (!window.location.hash.startsWith('#/403')) {
        window.location.hash = '#/403'
      }
      return Promise.reject(error)
    }

    // 非 401 错误
    ElMessage.error(
      error.response?.data?.message
      || error.response?.data?.detail
      || error.message
      || '网络错误',
    )
    return Promise.reject(error)
  },
)

// 泛型请求方法
export default request as <T>(config: any) => Promise<T>
