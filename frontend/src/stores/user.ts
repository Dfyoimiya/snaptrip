import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'
import type { UserInfo, LoginForm } from '@/types'
import { loginApi, logoutApi, getUserAccessApi, getUserInfoApi } from '@/apis/auth'
import { getUserInfo, setUserInfo, clearAuth, getToken, setToken, setRefreshToken, getRefreshToken, removeRefreshToken } from '@/utils/storage'
import { isTokenValid } from '@/utils/jwt'

export const useUserStore = defineStore('user', () => {
  // State
  const userInfo = reactive<UserInfo>({
    id: '',
    username: '',
    nickname: '',
    avatar: '',
    token: getToken() || '',
    menus: [],
    roles: [],
    permissions: [],
    ...getUserInfo<UserInfo>(),
  })

  // Getters
  const isLoggedIn = computed(() => isTokenValid(userInfo.token || getToken()))
  const username = computed(() => userInfo.username)
  const avatar = computed(() => userInfo.avatar)
  const permissions = computed(() => userInfo.permissions)

  function persistUserInfo() {
    setUserInfo({
      id: userInfo.id,
      username: userInfo.username,
      nickname: userInfo.nickname,
      avatar: userInfo.avatar,
      menus: userInfo.menus,
      roles: userInfo.roles,
      permissions: userInfo.permissions,
    })
  }

  async function loadProfileAndAccess() {
    const [meRes, accessRes] = await Promise.all([
      getUserInfoApi(),
      getUserAccessApi(),
    ])
    const me = meRes.data
    userInfo.id = me.id
    userInfo.username = me.email
    userInfo.nickname = me.nickname || me.email
    userInfo.avatar = me.avatarUrl || ''
    userInfo.menus = accessRes.data.menus
    userInfo.roles = accessRes.data.roles
    userInfo.permissions = accessRes.data.permissions
    persistUserInfo()
  }

  // Actions
  /** 登录 */
  async function login(form: LoginForm) {
    // 1. 调用登录接口
    const loginRes = await loginApi(form)
    // 响应拦截器已将 snake_case 转换为 camelCase
    const { accessToken, refreshToken } = loginRes.data

    // 2. 保存 token 和 refresh_token
    setToken(accessToken)
    setRefreshToken(refreshToken)
    userInfo.token = accessToken

    // 3. 获取用户信息
    try {
      await loadProfileAndAccess()
    } catch (error) {
      clearAuth()
      userInfo.token = ''
      throw error
    }

    return userInfo
  }

  /** 登出 */
  async function logout() {
    const rt = getRefreshToken()
    try {
      await logoutApi(rt || undefined)
      removeRefreshToken()
    } catch {
      // 即使后端登出失败也清除本地状态
    }
    clearAuth()
    userInfo.username = ''
    userInfo.id = ''
    userInfo.nickname = ''
    userInfo.avatar = ''
    userInfo.token = ''
    userInfo.menus = []
    userInfo.roles = []
    userInfo.permissions = []
  }

  return {
    userInfo,
    isLoggedIn,
    username,
    avatar,
    permissions,
    login,
    loadProfileAndAccess,
    logout,
  }
})
