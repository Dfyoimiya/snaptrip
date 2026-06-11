<script setup lang="ts">
/**
 * ============================================
 * 注册页面 (RegisterView)
 * 完整表单正则校验 + Mock 注册
 * ============================================
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registerAPI } from '@/apis/member'
import { useMemberStore } from '@/stores/member'

const router = useRouter()
const route = useRoute()
const memberStore = useMemberStore()

/** 注册表单 */
const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
  telephone: '',
  authCode: '',
})
/** 表单错误 */
const errors = ref<Record<string, string>>({})
/** 加载状态 */
const loading = ref(false)
/** 验证码倒计时 */
const countdown = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

/**
 * 表单校验规则
 */
const validateForm = (): boolean => {
  const errs: Record<string, string> = {}

  // 用户名：必填，2-20位，字母数字下划线
  if (!form.value.username) {
    errs.username = '请输入用户名'
  } else if (form.value.username.length < 2 || form.value.username.length > 20) {
    errs.username = '用户名长度应为2-20位'
  } else if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(form.value.username)) {
    errs.username = '用户名只能包含字母、数字、下划线'
  }

  // 密码：必填，6-20位，必须包含字母和数字
  if (!form.value.password) {
    errs.password = '请输入密码'
  } else if (form.value.password.length < 6 || form.value.password.length > 20) {
    errs.password = '密码长度应为6-20位'
  } else if (!/^(?=.*[a-zA-Z])(?=.*\d).+$/.test(form.value.password)) {
    errs.password = '密码必须同时包含字母和数字'
  }

  // 确认密码
  if (!form.value.confirmPassword) {
    errs.confirmPassword = '请确认密码'
  } else if (form.value.password !== form.value.confirmPassword) {
    errs.confirmPassword = '两次输入的密码不一致'
  }

  // 手机号：必填，11位
  if (!form.value.telephone) {
    errs.telephone = '请输入手机号'
  } else if (!/^1[3-9]\d{9}$/.test(form.value.telephone)) {
    errs.telephone = '请输入正确的11位手机号'
  }

  // 验证码：必填，6位数字
  if (!form.value.authCode) {
    errs.authCode = '请输入验证码'
  } else if (!/^\d{6}$/.test(form.value.authCode)) {
    errs.authCode = '验证码为6位数字'
  }

  errors.value = errs
  return Object.keys(errs).length === 0
}

/**
 * 清除字段错误
 */
const clearError = (field: string) => {
  delete errors.value[field]
}

/**
 * 发送验证码
 */
const sendAuthCode = () => {
  // 先校验手机号
  if (!form.value.telephone) {
    errors.value.telephone = '请先输入手机号'
    return
  }
  if (!/^1[3-9]\d{9}$/.test(form.value.telephone)) {
    errors.value.telephone = '请输入正确的11位手机号'
    return
  }
  delete errors.value.telephone

  if (countdown.value > 0) return
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  if (!validateForm()) return

  loading.value = true
  errors.value = {}

  try {
    await registerAPI({
      username: form.value.username,
      password: form.value.password,
      telephone: form.value.telephone,
      authCode: form.value.authCode,
    })
    router.push('/login')
  } catch {
    // Mock 注册（演示模式）
    handleMockRegister()
  } finally {
    loading.value = false
  }
}

/**
 * Mock 注册（演示模式）
 */
const handleMockRegister = () => {
  memberStore.setLoginInfo('mock-token-' + Date.now(), 'Bearer ')
  memberStore.setMemberInfo({
    id: Date.now(),
    memberLevelId: 1,
    username: form.value.username,
    nickname: form.value.username,
    phone: form.value.telephone,
    icon: '',
    gender: 0,
    birthday: '',
    city: '',
    personalizedSignature: '',
    integration: 100,
    growth: 0,
    loginCount: 1,
    attentionCount: 0,
    collectProductCount: 0,
    readCount: 0,
    couponCount: 3,
  })
  const redirect = route.query.redirect as string
  router.push(redirect || '/')
}
</script>

<template>
  <div class="min-h-[65vh] flex items-center justify-center py-10">
    <div class="w-full max-w-[420px]">
      <!-- 注册卡片 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <!-- 标题 -->
        <div class="text-center mb-8">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">创建账号</h1>
          <p class="text-sm text-gray-500 mt-2">注册后即可开始购物</p>
        </div>

        <!-- 注册表单 -->
        <form class="space-y-4" @submit.prevent="handleRegister">
          <!-- 用户名 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              用户名 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.username"
              type="text"
              placeholder="2-20位，支持字母、数字、下划线"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.username ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-red-500']"
              @input="clearError('username')"
            />
            <p v-if="errors.username" class="text-xs text-red-500 mt-1 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ errors.username }}
            </p>
          </div>

          <!-- 密码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              密码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              placeholder="6-20位，需同时包含字母和数字"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.password ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-red-500']"
              @input="clearError('password')"
            />
            <p v-if="errors.password" class="text-xs text-red-500 mt-1 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ errors.password }}
            </p>
            <!-- 密码强度条 -->
            <div v-if="form.password" class="flex items-center gap-2 mt-1.5">
              <div class="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="form.password.length >= 10 && /[a-z]/.test(form.password) && /[A-Z]/.test(form.password) && /\d/.test(form.password) ? 'bg-green-500 w-full' : form.password.length >= 8 ? 'bg-yellow-500 w-2/3' : 'bg-red-500 w-1/3'"
                />
              </div>
              <span class="text-xs text-gray-400">
                {{ form.password.length >= 10 && /[a-z]/.test(form.password) && /[A-Z]/.test(form.password) ? '强' : form.password.length >= 8 ? '中' : '弱' }}
              </span>
            </div>
          </div>

          <!-- 确认密码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              确认密码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.confirmPassword ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-red-500']"
              @input="clearError('confirmPassword')"
            />
            <p v-if="errors.confirmPassword" class="text-xs text-red-500 mt-1 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ errors.confirmPassword }}
            </p>
          </div>

          <!-- 手机号 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              手机号 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.telephone"
              type="tel"
              maxlength="11"
              placeholder="请输入11位手机号"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.telephone ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-red-500']"
              @input="clearError('telephone')"
            />
            <p v-if="errors.telephone" class="text-xs text-red-500 mt-1 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ errors.telephone }}
            </p>
          </div>

          <!-- 验证码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              验证码 <span class="text-red-500">*</span>
            </label>
            <div class="flex gap-3">
              <input
                v-model="form.authCode"
                type="text"
                maxlength="6"
                placeholder="6位数字验证码"
                :class="['flex-1 h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.authCode ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-red-500']"
                @input="clearError('authCode')"
              />
              <button
                type="button"
                :disabled="countdown > 0"
                class="h-11 px-5 border border-red-600 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:border-gray-300 disabled:text-gray-400 disabled:hover:bg-transparent transition-colors flex-shrink-0"
                @click="sendAuthCode"
              >
                {{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}
              </button>
            </div>
            <p v-if="errors.authCode" class="text-xs text-red-500 mt-1 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ errors.authCode }}
            </p>
          </div>

          <!-- 协议 -->
          <label class="flex items-start gap-2 text-sm text-gray-500 cursor-pointer">
            <input type="checkbox" checked class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 mt-0.5" />
            <span>我已阅读并同意 <button type="button" class="text-red-600 hover:underline">用户协议</button> 和 <button type="button" class="text-red-600 hover:underline">隐私政策</button></span>
          </label>

          <!-- 注册按钮 -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full h-12 bg-red-600 text-white font-bold text-base rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md shadow-red-200"
          >
            {{ loading ? '注册中...' : '注 册' }}
          </button>
        </form>

        <!-- 底部链接 -->
        <div class="mt-6 text-center text-sm">
          <span class="text-gray-500">已有账号？</span>
          <button class="text-red-600 hover:text-red-700 font-medium ml-1" @click="$router.push('/login')">
            去登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
