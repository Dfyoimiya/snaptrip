import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'
import type { UserInfo, LoginForm } from '@/types'
import { loginApi, logoutApi } from '@/apis/auth'
import { getUserInfo, setUserInfo, clearAuth, getToken } from '@/utils/storage'

export const useUserStore = defineStore('user', () => {
  // State
  const userInfo = reactive<UserInfo>({
    username: '',
    nickname: '',
    avatar: '',
    token: getToken() || '',
    menus: [],
    roles: [],
    ...getUserInfo<UserInfo>(),
  })

  // Getters
  const isLoggedIn = computed(() => !!userInfo.token)
  const username = computed(() => userInfo.username)
  const avatar = computed(() => userInfo.avatar)

  // Actions
  /** 登录 */
  async function login(form: LoginForm) {
    const res = await loginApi(form)
    const data = res.data
    Object.assign(userInfo, data)
    setUserInfo(data)
    return data
  }

  /** 登出 */
  async function logout() {
    await logoutApi()
    clearAuth()
    userInfo.username = ''
    userInfo.nickname = ''
    userInfo.avatar = ''
    userInfo.token = ''
    userInfo.menus = []
    userInfo.roles = []
  }

  return {
    userInfo,
    isLoggedIn,
    username,
    avatar,
    login,
    logout,
  }
})
