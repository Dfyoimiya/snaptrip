<script setup lang="ts">
/**
 * ============================================
 * 账号设置页 (MemberSettingsView)
 * 个人中心侧边栏子路由
 * 包含：修改密码、绑定手机、退出登录
 * ============================================
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'

const router = useRouter()
const memberStore = useMemberStore()

/** 当前激活的设置项 */
const activeSetting = ref<'password' | 'phone' | 'logout'>('password')

/** 修改密码表单 */
const pwdForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const pwdErrors = ref<Record<string, string>>({})
const pwdSuccess = ref(false)

/** 绑定手机表单 */
const phoneForm = ref({
  phone: memberStore.memberInfo?.phone || '',
  authCode: '',
})
const phoneErrors = ref<Record<string, string>>({})

/** 表单校验规则 */
const validatePassword = () => {
  const errors: Record<string, string> = {}
  if (!pwdForm.value.oldPassword) {
    errors.oldPassword = '请输入当前密码'
  }
  if (!pwdForm.value.newPassword) {
    errors.newPassword = '请输入新密码'
  } else if (pwdForm.value.newPassword.length < 6) {
    errors.newPassword = '密码长度不能少于6位'
  } else if (pwdForm.value.newPassword.length > 20) {
    errors.newPassword = '密码长度不能超过20位'
  } else if (!/^(?=.*[a-zA-Z])(?=.*\d)/.test(pwdForm.value.newPassword)) {
    errors.newPassword = '密码必须包含字母和数字'
  }
  if (!pwdForm.value.confirmPassword) {
    errors.confirmPassword = '请确认新密码'
  } else if (pwdForm.value.newPassword !== pwdForm.value.confirmPassword) {
    errors.confirmPassword = '两次输入的密码不一致'
  }
  pwdErrors.value = errors
  return Object.keys(errors).length === 0
}

const validatePhone = () => {
  const errors: Record<string, string> = {}
  if (!phoneForm.value.phone) {
    errors.phone = '请输入手机号'
  } else if (!/^1[3-9]\d{9}$/.test(phoneForm.value.phone)) {
    errors.phone = '请输入正确的手机号'
  }
  if (!phoneForm.value.authCode) {
    errors.authCode = '请输入验证码'
  } else if (!/^\d{6}$/.test(phoneForm.value.authCode)) {
    errors.authCode = '验证码为6位数字'
  }
  phoneErrors.value = errors
  return Object.keys(errors).length === 0
}

/** 提交修改密码 */
const handleChangePassword = async () => {
  if (!validatePassword()) return
  // Mock 成功
  pwdSuccess.value = true
  pwdForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  setTimeout(() => { pwdSuccess.value = false }, 3000)
}

/** 提交绑定手机 */
const handleBindPhone = async () => {
  if (!validatePhone()) return
  // Mock 成功
  if (memberStore.memberInfo) {
    memberStore.memberInfo.phone = phoneForm.value.phone
  }
}

/** 倒计时 */
const countdown = ref(0)
let timer: ReturnType<typeof setInterval> | null = null
const startCountdown = () => {
  if (countdown.value > 0) return
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && timer) {
      clearInterval(timer)
    }
  }, 1000)
}

/** 退出登录 */
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    memberStore.memberLogout()
    router.push('/')
  }
}

/** 设置菜单 */
const settingMenus = [
  { key: 'password' as const, label: '修改密码', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
  { key: 'phone' as const, label: '绑定手机', icon: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z' },
  { key: 'logout' as const, label: '退出登录', icon: 'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1' },
]
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <!-- 标题 -->
    <div class="px-6 py-4 border-b border-gray-100">
      <h2 class="text-lg font-bold text-gray-900">账号设置</h2>
    </div>

    <div class="flex">
      <!-- 左侧子菜单 -->
      <aside class="w-48 border-r border-gray-100 py-3">
        <button
          v-for="menu in settingMenus"
          :key="menu.key"
          :class="[
            'w-full flex items-center gap-3 px-5 py-3 text-sm transition-colors text-left',
            activeSetting === menu.key
              ? 'text-red-600 bg-red-50 font-medium border-l-3 border-red-600'
              : 'text-gray-600 hover:bg-gray-50',
          ]"
          @click="activeSetting = menu.key"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" :d="menu.icon" />
          </svg>
          <span>{{ menu.label }}</span>
        </button>
      </aside>

      <!-- 右侧内容 -->
      <div class="flex-1 p-8">
        <!-- ====== 修改密码 ====== -->
        <div v-if="activeSetting === 'password'" class="max-w-md">
          <h3 class="text-base font-bold text-gray-900 mb-1">修改密码</h3>
          <p class="text-sm text-gray-400 mb-6">定期修改密码可以保护您的账号安全</p>

          <!-- 成功提示 -->
          <div v-if="pwdSuccess" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-600 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            密码修改成功！
          </div>

          <form class="space-y-4" @submit.prevent="handleChangePassword">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
              <input
                v-model="pwdForm.oldPassword"
                type="password"
                placeholder="请输入当前密码"
                :class="[
                  'w-full h-11 px-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                  pwdErrors.oldPassword ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
                ]"
              />
              <p v-if="pwdErrors.oldPassword" class="text-xs text-red-500 mt-1">{{ pwdErrors.oldPassword }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
              <input
                v-model="pwdForm.newPassword"
                type="password"
                placeholder="6-20位，需包含字母和数字"
                :class="[
                  'w-full h-11 px-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                  pwdErrors.newPassword ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
                ]"
              />
              <p v-if="pwdErrors.newPassword" class="text-xs text-red-500 mt-1">{{ pwdErrors.newPassword }}</p>
              <div class="flex items-center gap-1 mt-1.5">
                <div class="h-1 flex-1 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="pwdForm.newPassword.length >= 10 ? 'bg-green-500 w-full' : pwdForm.newPassword.length >= 6 ? 'bg-yellow-500 w-2/3' : pwdForm.newPassword.length > 0 ? 'bg-red-500 w-1/3' : 'w-0'"
                  />
                </div>
                <span class="text-xs text-gray-400">
                  {{ pwdForm.newPassword.length >= 10 ? '强' : pwdForm.newPassword.length >= 6 ? '中' : pwdForm.newPassword.length > 0 ? '弱' : '' }}
                </span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
              <input
                v-model="pwdForm.confirmPassword"
                type="password"
                placeholder="请再次输入新密码"
                :class="[
                  'w-full h-11 px-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                  pwdErrors.confirmPassword ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
                ]"
              />
              <p v-if="pwdErrors.confirmPassword" class="text-xs text-red-500 mt-1">{{ pwdErrors.confirmPassword }}</p>
            </div>

            <button
              type="submit"
              class="w-full h-11 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors"
            >
              确认修改
            </button>
          </form>
        </div>

        <!-- ====== 绑定手机 ====== -->
        <div v-if="activeSetting === 'phone'" class="max-w-md">
          <h3 class="text-base font-bold text-gray-900 mb-1">绑定手机</h3>
          <p class="text-sm text-gray-400 mb-6">绑定手机号可用于登录和接收订单通知</p>

          <form class="space-y-4" @submit.prevent="handleBindPhone">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">手机号</label>
              <input
                v-model="phoneForm.phone"
                type="tel"
                placeholder="请输入11位手机号"
                maxlength="11"
                :class="[
                  'w-full h-11 px-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                  phoneErrors.phone ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
                ]"
              />
              <p v-if="phoneErrors.phone" class="text-xs text-red-500 mt-1">{{ phoneErrors.phone }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">验证码</label>
              <div class="flex gap-3">
                <input
                  v-model="phoneForm.authCode"
                  type="text"
                  placeholder="6位数字验证码"
                  maxlength="6"
                  :class="[
                    'flex-1 h-11 px-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                    phoneErrors.authCode ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
                  ]"
                />
                <button
                  type="button"
                  :disabled="countdown > 0"
                  class="h-11 px-5 border border-red-600 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:border-gray-300 disabled:text-gray-400 disabled:hover:bg-transparent transition-colors flex-shrink-0"
                  @click="startCountdown"
                >
                  {{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}
                </button>
              </div>
              <p v-if="phoneErrors.authCode" class="text-xs text-red-500 mt-1">{{ phoneErrors.authCode }}</p>
            </div>

            <button
              type="submit"
              class="w-full h-11 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors"
            >
              确认绑定
            </button>
          </form>
        </div>

        <!-- ====== 退出登录 ====== -->
        <div v-if="activeSetting === 'logout'" class="max-w-md">
          <h3 class="text-base font-bold text-gray-900 mb-1">退出登录</h3>
          <p class="text-sm text-gray-400 mb-6">退出后将清除本地登录状态，需要重新登录</p>

          <div class="bg-gray-50 rounded-lg p-5 mb-6">
            <div class="flex items-center gap-4">
              <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <span class="text-xl font-bold text-red-600">{{ memberStore.displayName.charAt(0).toUpperCase() }}</span>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900">{{ memberStore.displayName }}</p>
                <p class="text-xs text-gray-500 mt-1">{{ memberStore.memberInfo?.phone || '138****8888' }}</p>
              </div>
            </div>
          </div>

          <button
            class="w-full h-11 border border-red-600 text-red-600 font-medium rounded-lg hover:bg-red-50 transition-colors"
            @click="handleLogout"
          >
            确认退出登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
