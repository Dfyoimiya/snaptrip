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
import router from '@/router'

// 请求基地址（从环境变量读取）
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

// 创建 Axios 实例
const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'source-client': 'pc',
  },
})

/**
 * 请求拦截器
 * 1. 添加 Authorization Token
 * 2. 设置请求头
 */
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const memberStore = useMemberStore()
    const token = memberStore.token
    if (token) {
      config.headers.Authorization = `${memberStore.tokenHead}${token}`
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
 * 3. 401 未授权处理
 */
request.interceptors.response.use(
  (response: AxiosResponse<CommonResult<unknown>>) => {
    const { data } = response
    if (data.code === 200) {
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
  (error) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as CommonResult<unknown> | undefined
      const message = data?.message || '请求错误'

      if (status === 401) {
        // HTTP 401 兜底
        const memberStore = useMemberStore()
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
    return Promise.reject(new Error('网络错误，请检查网络连接'))
  },
)

/**
 * 封装 GET 请求
 * @param url 请求地址
 * @param params 查询参数
 * @param config 额外配置
 */
export function get<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request
    .get<CommonResult<T>>(url, { params, ...config })
    .then((res) => res.data.data)
}

/**
 * 封装 POST 请求
 * @param url 请求地址
 * @param data 请求体数据
 * @param config 额外配置
 */
export function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request
    .post<CommonResult<T>>(url, data, config)
    .then((res) => res.data.data)
}

/**
 * 封装 PUT 请求
 * @param url 请求地址
 * @param data 请求体数据
 * @param config 额外配置
 */
export function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request
    .put<CommonResult<T>>(url, data, config)
    .then((res) => res.data.data)
}

/**
 * 封装 DELETE 请求
 * @param url 请求地址
 * @param params 查询参数
 * @param config 额外配置
 */
export function del<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request
    .delete<CommonResult<T>>(url, { params, ...config })
    .then((res) => res.data.data)
}

export default request
