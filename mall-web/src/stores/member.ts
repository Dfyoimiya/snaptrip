/**
 * ============================================
 * 会员状态管理 (Pinia Store)
 * ============================================
 */

import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { MemberInfo } from '@/types/member'
import { logoutAPI } from '@/apis/member'

const STORAGE_KEY = 'snaptrip_member'

function loadPersisted(): { token: string; refreshToken: string; memberInfo: MemberInfo | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { token: '', refreshToken: '', memberInfo: null }
}

function savePersisted(token: string, refreshToken: string, memberInfo: MemberInfo | null) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, refreshToken, memberInfo }))
  } catch { /* ignore */ }
}

export const useMemberStore = defineStore('member', () => {
  const persisted = loadPersisted()

  const token = ref<string>(persisted.token)
  const refreshToken = ref<string>(persisted.refreshToken)
  const memberInfo = ref<MemberInfo | null>(persisted.memberInfo)

  watch([token, refreshToken, memberInfo], () => {
    savePersisted(token.value, refreshToken.value, memberInfo.value)
  }, { deep: true })

  const isLoggedIn = computed(() => !!token.value)
  const displayName = computed(() => memberInfo.value?.nickname || memberInfo.value?.email || '')
  const avatar = computed(() => memberInfo.value?.avatarUrl || '')
  const integration = computed(() => memberInfo.value?.integration || 0)

  const setLoginInfo = (accessToken: string, refresh: string, info?: MemberInfo) => {
    token.value = accessToken
    refreshToken.value = refresh
    if (info) memberInfo.value = info
  }

  const setMemberInfo = (info: MemberInfo) => {
    memberInfo.value = info
  }

  const memberLogout = async () => {
    const rt = refreshToken.value
    token.value = ''
    refreshToken.value = ''
    memberInfo.value = null
    if (rt) {
      try { await logoutAPI(rt) } catch { /* ignore */ }
    }
  }

  return {
    token,
    refreshToken,
    memberInfo,
    isLoggedIn,
    displayName,
    avatar,
    integration,
    setLoginInfo,
    setMemberInfo,
    memberLogout,
  }
})
