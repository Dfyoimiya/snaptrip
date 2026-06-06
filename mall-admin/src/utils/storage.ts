/** Token 存储 Key */
const TOKEN_KEY = 'admin_token'
const USER_INFO_KEY = 'admin_user_info'

/** 获取 Token */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/** 设置 Token */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 移除 Token */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** 获取用户信息 */
export function getUserInfo<T>(): T | null {
  const data = localStorage.getItem(USER_INFO_KEY)
  return data ? JSON.parse(data) : null
}

/** 设置用户信息 */
export function setUserInfo<T>(info: T): void {
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
}

/** 移除用户信息 */
export function removeUserInfo(): void {
  localStorage.removeItem(USER_INFO_KEY)
}

/** 清除所有认证信息 */
export function clearAuth(): void {
  removeToken()
  removeUserInfo()
}
