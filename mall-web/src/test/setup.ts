/**
 * Vitest 全局环境配置 (mall-web C-end)
 * 在每个测试文件执行前运行，注入公共 Mock
 */

import { config } from '@vue/test-utils'

// ─── 项目级别的全局 stub ─────────────────────────────────────
// Tailwind-based 组件不需要额外的 UI 库 stub

config.global.stubs = {
  'router-link': { template: '<a><slot /></a>', props: ['to'] },
  'router-view': { template: '<div><slot /></div>' },
  // 常见 SVG 图标 stub
  'HeroIcon': { template: '<svg />' },
}

// ─── LocalStorage Mock ────────────────────────────────────────
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem(key: string): string | null {
      return store[key] ?? null
    },
    setItem(key: string, value: string): void {
      store[key] = value
    },
    removeItem(key: string): void {
      delete store[key]
    },
    clear(): void {
      store = {}
    },
    get length(): number {
      return Object.keys(store).length
    },
    key(index: number): string | null {
      return Object.keys(store)[index] ?? null
    },
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// ─── matchMedia Mock (Tailwind responsive 相关) ───────────────
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// ─── IntersectionObserver Mock ────────────────────────────────
class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
})
