/**
 * ============================================
 * 会员状态管理 (Pinia Store)
 * ============================================
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { MemberInfo } from '@/types/member'

export const useMemberStore = defineStore(
  'member',
  () => {
    // ===== State =====
    /** JWT Token */
    const token = ref<string>('')
    /** Token 前缀 */
    const tokenHead = ref<string>('Bearer ')
    /** 会员信息 */
    const memberInfo = ref<MemberInfo | null>(null)

    // ===== Getters =====
    /** 是否已登录 */
    const isLoggedIn = computed(() => !!token.value && !!memberInfo.value)
    /** 会员昵称（优先显示昵称，否则显示用户名） */
    const displayName = computed(() => memberInfo.value?.nickname || memberInfo.value?.username || '')
    /** 会员头像 */
    const avatar = computed(() => memberInfo.value?.icon || '')
    /** 会员积分 */
    const integration = computed(() => memberInfo.value?.integration || 0)

    // ===== Actions =====
    /**
     * 设置登录信息
     */
    const setLoginInfo = (newToken: string, newTokenHead: string, info?: MemberInfo) => {
      token.value = newToken
      tokenHead.value = newTokenHead
      if (info) {
        memberInfo.value = info
      }
    }

    /**
     * 设置会员信息
     */
    const setMemberInfo = (info: MemberInfo) => {
      memberInfo.value = info
    }

    /**
     * 会员登出
     */
    const memberLogout = () => {
      token.value = ''
      tokenHead.value = 'Bearer '
      memberInfo.value = null
    }

    return {
      token,
      tokenHead,
      memberInfo,
      isLoggedIn,
      displayName,
      avatar,
      integration,
      setLoginInfo,
      setMemberInfo,
      memberLogout,
    }
  },
  {
    persist: true,
  },
)
