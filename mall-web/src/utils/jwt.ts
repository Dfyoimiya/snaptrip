/** JWT 解析工具 —— 纯前端解码，不验证签名 */

/** 解析 JWT payload（不验证签名，仅用于读取 exp 等公开字段） */
export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    if (!payload) return null
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

/** 检查 JWT 是否已过期（提前 60 秒视为过期，避免网络延迟导致刚好过期） */
export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') {
    return true
  }
  const nowSeconds = Math.floor(Date.now() / 1000)
  return payload.exp <= nowSeconds + 60
}

/** 检查 JWT 是否有效 */
export function isTokenValid(token: string | null): boolean {
  if (!token) return false
  return !isTokenExpired(token)
}
