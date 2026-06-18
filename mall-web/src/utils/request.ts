/**
 * ============================================
 * Axios 请求封装
 * 基于 Axios 的 HTTP 请求工具，适配 PC Web 端
 * ============================================
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { CommonResult } from '@/types/common'
import { useMemberStore } from '@/stores/member'
import { isTokenExpired } from './jwt'
import router from '@/router'

// 开发环境统一走 Vite 同源代理；生产环境读取部署配置。
const baseURL = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE_URL || '')

interface APIErrorPayload {
  message?: string
  detail?: string | Array<{ msg?: string }>
}

function getErrorMessage(data: APIErrorPayload | undefined, fallback: string): string {
  if (!data) return fallback
  if (data.message) return data.message
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) {
    const validationMessage = data.detail
      .map((item) => item.msg)
      .filter((message): message is string => Boolean(message))
      .join('；')
    if (validationMessage) return validationMessage
  }
  return fallback
}

// ── snake_case → camelCase 深度转换 ────────────────────────────────────────

const snakeToCamel = (key: string): string =>
  key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())

const deepConvertKeys = (obj: unknown): unknown => {
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

// ── Token 刷新队列（防止并发 401 时重复刷新） ────────────────────────

let isRefreshing = false
let pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: any) => void
}> = []

function addPendingRequest(resolve: (token: string) => void, reject: (error: any) => void) {
  pendingRequests.push({ resolve, reject })
}

function processPendingRequests(token: string) {
  pendingRequests.forEach(({ resolve }) => resolve(token))
  pendingRequests = []
}

function rejectPendingRequests(error: any) {
  pendingRequests.forEach(({ reject }) => reject(error))
  pendingRequests = []
}

async function refreshAndRetry(): Promise<string> {
  const memberStore = useMemberStore()
  const refreshToken = memberStore.refreshToken
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const response = await axios.post(
    `${baseURL}/api/v1/auth/refresh`,
    { refresh_token: refreshToken },
    { timeout: 10000 },
  )
  const res = response.data
  if (res.code !== 0 || !res.data) {
    throw new Error(res.message || 'Token refresh failed')
  }
  const { accessToken, refreshToken: newRefreshToken } = res.data
  memberStore.setLoginInfo(accessToken, newRefreshToken, memberStore.memberInfo ?? undefined)
  return accessToken
}

// 创建 Axios 实例
const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'source-client': 'pc',
  },
})

/**
 * 请求拦截器
 * 1. 添加 Authorization Token
 * 2. Token 即将过期时提前刷新
 */
request.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const memberStore = useMemberStore()
    const token = memberStore.token

    // 检查 token 是否即将过期，提前刷新
    if (token && isTokenExpired(token) && !config.url?.includes('/auth/refresh') && !config.url?.includes('/auth/logout')) {
      if (isRefreshing) {
        return new Promise<InternalAxiosRequestConfig>((resolve, reject) => {
          addPendingRequest(
            (newToken: string) => {
              config.headers.Authorization = `Bearer ${newToken}`
              resolve(config)
            },
            (err: any) => reject(err),
          )
        })
      }

      isRefreshing = true
      try {
        const newToken = await refreshAndRetry()
        isRefreshing = false
        processPendingRequests(newToken)
        config.headers.Authorization = `Bearer ${newToken}`
        return config
      } catch {
        isRefreshing = false
        rejectPendingRequests(new Error('Token refresh failed'))
        // 刷新失败，清除过期 token，以无认证状态发送请求
        memberStore.memberLogout()
        delete config.headers.Authorization
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

/**
 * 响应拦截器
 * 1. 提取核心数据
 * 2. 统一错误处理
 * 3. 401 未授权处理 + 静默刷新
 */
request.interceptors.response.use(
  (response: AxiosResponse<CommonResult<unknown>>) => {
    const { data } = response
    // Backend returns code=0 for success
    if (data.code === 0) {
      // 深度转换 snake_case → camelCase
      if (data.data) {
        response.data = { ...data, data: deepConvertKeys(data.data) }
      }
      return response
    }
    // mall 后端认证过期返回 HTTP 200 + code=401
    if (data.code === 401) {
      const memberStore = useMemberStore()
      memberStore.memberLogout()
      router.push('/login')
      console.error('[Auth Error] 登录已过期，请重新登录')
      return Promise.reject(new Error(data.message || '登录已过期'))
    }
    // 业务错误处理
    const errorMsg = data.message || '请求错误'
    console.error(`[API Error] ${errorMsg}`, data)
    return Promise.reject(new Error(errorMsg))
  },
  async (error) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as (CommonResult<unknown> & APIErrorPayload) | undefined
      const message = getErrorMessage(data, '请求错误')

      if (status === 401) {
        // 登录/注册端点的 401 是正常业务响应，不应触发 token 刷新
        const isAuthEndpoint = error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/register')
        if (isAuthEndpoint) {
          return Promise.reject(new Error(message))
        }

        // HTTP 401 — 尝试静默刷新 token
        const memberStore = useMemberStore()
        if (memberStore.refreshToken && !error.config?.url?.includes('/auth/refresh') && !error.config?.url?.includes('/auth/logout')) {
          if (!isRefreshing) {
            isRefreshing = true
            try {
              const newToken = await refreshAndRetry()
              isRefreshing = false
              processPendingRequests(newToken)
              // 重试原始请求
              error.config.headers.Authorization = `Bearer ${newToken}`
              return request(error.config)
            } catch {
              isRefreshing = false
              rejectPendingRequests(new Error('Token refresh failed'))
            }
          } else {
            // 已在刷新中，将请求加入队列
            return new Promise((resolve, reject) => {
              addPendingRequest(
                (newToken: string) => {
                  error.config.headers.Authorization = `Bearer ${newToken}`
                  resolve(request(error.config))
                },
                (err: any) => reject(err),
              )
            })
          }
        }
        // 无 refresh token 或刷新本身失败 → 跳转登录
        memberStore.memberLogout()
        router.push('/login')
        console.error('[Auth Error] 登录已过期，请重新登录')
      } else {
        console.error(`[HTTP Error ${status}] ${message}`)
      }
      return Promise.reject(new Error(message))
    }
    // 网络错误
    console.error('[Network Error]', error.message)
    return Promise.reject(new Error('暂时无法连接服务器，请稍后重试'))
  },
)

/**
 * 封装 GET 请求
 */
export function get<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request
    .get<CommonResult<T>>(url, { params, ...config })
    .then((res) => res.data.data)
}

/**
 * 封装 POST 请求
 */
export function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request
    .post<CommonResult<T>>(url, data, { ...config })
    .then((res) => res.data.data)
}

/**
 * 封装 PUT 请求
 */
export function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request
    .put<CommonResult<T>>(url, data, config)
    .then((res) => res.data.data)
}

/**
 * 封装 DELETE 请求
 */
export function del<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request
    .delete<CommonResult<T>>(url, { params, ...config })
    .then((res) => res.data.data)
}

/**
 * 封装 PATCH 请求
 */
export function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request
    .patch<CommonResult<T>>(url, data, config)
    .then((res) => res.data.data)
}

export default request
