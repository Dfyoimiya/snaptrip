/**
 * JWT 解析工具测试
 * 覆盖: payload 解析、过期检测、有效性校验
 */

import { describe, it, expect } from 'vitest'
import { parseJwtPayload, isTokenExpired, isTokenValid } from '@/utils/jwt'

// 辅助函数：构造一个简单的 JWT（不签名）
function buildJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.fake-signature`
}

describe('parseJwtPayload', () => {
  it('should parse valid JWT payload', () => {
    const payload = { sub: '1', username: 'admin', exp: 9999999999 }
    const token = buildJwt(payload)
    const result = parseJwtPayload(token)
    expect(result).toEqual(payload)
  })

  it('should return null for malformed token (only 1 part)', () => {
    expect(parseJwtPayload('abc')).toBeNull()
  })

  it('should return null for malformed token (only 2 parts)', () => {
    const bad = `header.${btoa(JSON.stringify({ a: 1 }))}`
    expect(parseJwtPayload(bad)).toBeNull()
  })

  it('should return null for empty string', () => {
    expect(parseJwtPayload('')).toBeNull()
  })

  it('should return null for non-base64 payload', () => {
    const token = 'header.!!!invalid-base64.signature'
    expect(parseJwtPayload(token)).toBeNull()
  })
})

describe('isTokenExpired', () => {
  it('should return false for token expiring far in the future', () => {
    const token = buildJwt({ exp: Date.now() / 1000 + 3600 + 120 }) // 1h + 2min from now
    expect(isTokenExpired(token)).toBe(false)
  })

  it('should return true for token expired 1 second ago', () => {
    const token = buildJwt({ exp: Date.now() / 1000 - 1 })
    expect(isTokenExpired(token)).toBe(true)
  })

  it('should return true for token expiring within the 60-second buffer', () => {
    const token = buildJwt({ exp: Date.now() / 1000 + 30 })
    expect(isTokenExpired(token)).toBe(true)
  })

  it('should return true for token at exactly the buffer boundary', () => {
    const exp = Math.floor(Date.now() / 1000) + 60 // 刚好 60s 后（取整）
    const token = buildJwt({ exp })
    // exp <= now + 60 → 过期
    expect(isTokenExpired(token)).toBe(true)
  })

  it('should return true when exp field is missing', () => {
    const token = buildJwt({ sub: '1' })
    expect(isTokenExpired(token)).toBe(true)
  })

  it('should return true when payload is null', () => {
    expect(isTokenExpired('not-a-valid-token')).toBe(true)
  })
})

describe('isTokenValid', () => {
  it('should return true for valid future token', () => {
    const token = buildJwt({ exp: Date.now() / 1000 + 7200 })
    expect(isTokenValid(token)).toBe(true)
  })

  it('should return false for null', () => {
    expect(isTokenValid(null)).toBe(false)
  })

  it('should return false for undefined (type cast to null)', () => {
    expect(isTokenValid('')).toBe(false)
  })

  it('should return false for expired token', () => {
    const token = buildJwt({ exp: Date.now() / 1000 - 100 })
    expect(isTokenValid(token)).toBe(false)
  })
})
