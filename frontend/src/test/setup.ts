/**
 * Vitest 全局环境配置
 * 在每个测试文件执行前运行，注入公共 Mock
 */

import { config } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'

// ─── Element Plus 全局 Mock ───────────────────────────────────
// 避免测试中加载真实组件库导致的依赖问题
// Element Plus 组件在测试中作为 stub 处理

config.global.stubs = {
  // Element Plus 常用组件 stub
  'el-button': { template: '<button><slot /></button>' },
  'el-input': { template: '<input />' },
  'el-select': { template: '<select><slot /></select>' },
  'el-table': { template: '<table><slot /></table>' },
  'el-dialog': { template: '<div><slot /></div>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-menu': { template: '<div><slot /></div>' },
  'el-sub-menu': { template: '<div><slot /></div>' },
  'el-tag': { template: '<span><slot /></span>' },
  'el-icon': { template: '<i />' },
  'el-pagination': { template: '<div />' },
  'el-breadcrumb': { template: '<nav><slot /></nav>' },
  'el-breadcrumb-item': { template: '<span><slot /></span>' },
  'router-link': { template: '<a><slot /></a>', props: ['to'] },
  'router-view': { template: '<div><slot /></div>' },
}

// ─── Import Meta Mock (for Vite's import.meta.env) ────────────
// @ts-expect-error vitest global augmentation
globalThis.import = { meta: { env: { VITE_APP_BASE_API: 'http://localhost:8080' } } }

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
