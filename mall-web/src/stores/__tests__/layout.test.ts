import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLayoutStore } from '@/stores/layout'

describe('useLayoutStore theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
    document.documentElement.style.colorScheme = ''
    setActivePinia(createPinia())
  })

  it('uses light theme by default', () => {
    const store = useLayoutStore()

    expect(store.theme).toBe('light')
  })

  it('toggles, applies, and persists dark theme', () => {
    const store = useLayoutStore()

    store.toggleTheme()

    expect(store.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.style.colorScheme).toBe('dark')
    expect(localStorage.getItem('snaptrip_theme')).toBe('dark')
  })

  it('restores persisted dark theme', () => {
    localStorage.setItem('snaptrip_theme', 'dark')
    setActivePinia(createPinia())

    const store = useLayoutStore()
    store.applyTheme()

    expect(store.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
