<script setup lang="ts">
/**
 * ============================================
 * 登录页面 (LoginView)
 * ============================================
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginAPI, getMemberInfoAPI } from '@/apis/member'
import { useMemberStore } from '@/stores/member'

const route = useRoute()
const router = useRouter()
const memberStore = useMemberStore()

/** 登录表单 */
const form = ref({ email: '', password: '' })
/** 表单错误 */
const errors = ref<Record<string, string>>({})
/** 加载状态 */
const loading = ref(false)

/**
 * 表单校验规则
 */
const validateForm = (): boolean => {
  const errs: Record<string, string> = {}

  // 邮箱：必填，格式校验
  if (!form.value.email) {
    errs.email = '请输入邮箱'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    errs.email = '请输入有效的邮箱地址'
  }

  // 密码：必填，6-128位
  if (!form.value.password) {
    errs.password = '请输入密码'
  } else if (form.value.password.length < 6) {
    errs.password = '密码至少6位字符'
  } else if (form.value.password.length > 128) {
    errs.password = '密码最多128位字符'
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
 * 处理登录
 */
const handleLogin = async () => {
  if (!validateForm()) return

  loading.value = true
  errors.value = {}

  try {
    const loginRes = await loginAPI({
      email: form.value.email,
      password: form.value.password,
    })
    memberStore.setLoginInfo(loginRes.accessToken, loginRes.refreshToken)
    try {
      const memberInfo = await getMemberInfoAPI()
      memberStore.setMemberInfo(memberInfo)
    } catch { /* ignore */ }
    router.push((route.query.redirect as string) || '/')
  } catch (e: any) {
    errors.value.general = e?.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[65vh] flex items-center justify-center py-10">
    <div class="w-full max-w-[420px]">
      <!-- 登录卡片 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <!-- 标题 -->
        <div class="text-center mb-8">
          <div class="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">欢迎登录</h1>
          <p class="text-sm text-gray-500 mt-2">登录后即可享受完整购物体验</p>
        </div>

        <!-- 登录表单 -->
        <form class="space-y-5" @submit.prevent="handleLogin">
          <!-- 全局错误 -->
          <div v-if="errors.general" class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            {{ errors.general }}
          </div>

          <!-- 邮箱 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              邮箱 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.email"
              type="email"
              placeholder="请输入邮箱地址"
              :class="[
                'w-full h-12 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2',
                errors.email
                  ? 'border-red-300 focus:ring-red-200 bg-red-50/30'
                  : 'border-gray-300 focus:ring-brand-500 focus:border-transparent',
              ]"
              @input="clearError('email')"
            />
            <p v-if="errors.email" class="text-xs text-red-500 mt-1.5 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ errors.email }}
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
              placeholder="请输入密码（6-128位）"
              :class="[
                'w-full h-12 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2',
                errors.password
                  ? 'border-red-300 focus:ring-red-200 bg-red-50/30'
                  : 'border-gray-300 focus:ring-brand-500 focus:border-transparent',
              ]"
              @input="clearError('password')"
            />
            <p v-if="errors.password" class="text-xs text-red-500 mt-1.5 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ errors.password }}
            </p>
          </div>

          <!-- 登录按钮 -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full h-12 bg-brand-600 text-white font-bold text-base rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md shadow-brand-200"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </button>
        </form>

        <!-- 底部链接 -->
        <div class="mt-6 text-center text-sm">
          <span class="text-gray-500">还没有账号？</span>
          <button class="text-brand-600 hover:text-brand-700 font-medium ml-1" @click="$router.push('/register')">
            立即注册
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
