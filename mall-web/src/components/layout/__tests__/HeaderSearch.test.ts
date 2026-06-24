import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/apis/search', () => ({
  getSearchSuggestAPI: vi.fn().mockResolvedValue({ sections: [] }),
}))

vi.mock('@/utils/tracker', () => ({
  trackSearch: vi.fn(),
}))

import HeaderSearch from '@/components/layout/HeaderSearch.vue'

const HISTORY_KEY = '_snaptrip_search_history'

async function mountHeaderSearch() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  })
  await router.push('/')
  await router.isReady()

  return mount(HeaderSearch, {
    props: { mode: 'inline' },
    global: { plugins: [router] },
  })
}

describe('HeaderSearch history', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('clears every search history item immediately', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['积木', '手机']))
    const wrapper = await mountHeaderSearch()

    expect(wrapper.text()).toContain('积木')
    expect(wrapper.text()).toContain('手机')

    const clearButton = wrapper.findAll('button').find((button) => button.text() === '清除')
    await clearButton?.trigger('pointerdown')

    expect(wrapper.text()).not.toContain('搜索历史')
    expect(localStorage.getItem(HISTORY_KEY)).toBeNull()
  })

  it('removes one history item without affecting the others', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['积木', '手机']))
    const wrapper = await mountHeaderSearch()

    const deleteButton = wrapper.find('button[aria-label="删除搜索历史：积木"]')
    await deleteButton.trigger('pointerdown')

    expect(wrapper.text()).not.toContain('积木')
    expect(wrapper.text()).toContain('手机')
    expect(JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')).toEqual(['手机'])
  })
})
