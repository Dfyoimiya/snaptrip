<script setup lang="ts">
/**
 * ============================================
 * 登录页面 (LoginView)
 * 完整表单正则校验 + Mock 登录
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
const form = ref({ username: '', password: '' })
/** 表单错误 */
const errors = ref<Record<string, string>>({})
/** 加载状态 */
const loading = ref(false)

/**
 * 表单校验规则
 */
const validateForm = (): boolean => {
  const errs: Record<string, string> = {}

  // 用户名：必填，2-20位
  if (!form.value.username) {
    errs.username = '请输入用户名'
  } else if (form.value.username.length < 2) {
    errs.username = '用户名至少2位字符'
  } else if (form.value.username.length > 20) {
    errs.username = '用户名最多20位字符'
  } else if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(form.value.username)) {
    errs.username = '用户名只能包含字母、数字、下划线'
  }

  // 密码：必填，6-20位
  if (!form.value.password) {
    errs.password = '请输入密码'
  } else if (form.value.password.length < 6) {
    errs.password = '密码至少6位字符'
  } else if (form.value.password.length > 20) {
    errs.password = '密码最多20位字符'
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
      username: form.value.username,
      password: form.value.password,
    })
    memberStore.setLoginInfo(loginRes.token, loginRes.tokenHead)
    try {
      const memberInfo = await getMemberInfoAPI()
      memberStore.setMemberInfo(memberInfo)
    } catch { /* ignore */ }
    router.push((route.query.redirect as string) || '/')
  } catch {
    // Mock 登录（演示模式，无后端时自动降级）
    handleMockLogin()
  } finally {
    loading.value = false
  }
}

/**
 * Mock 登录（演示模式）
 */
const handleMockLogin = () => {
  memberStore.setLoginInfo('mock-token-' + Date.now(), 'Bearer ')
  memberStore.setMemberInfo({
    id: 1,
    memberLevelId: 1,
    username: form.value.username,
    nickname: form.value.username,
    phone: '138****8888',
    icon: '',
    gender: 0,
    birthday: '',
    city: '上海',
    personalizedSignature: '热爱购物，品质生活',
    integration: 2580,
    growth: 3600,
    loginCount: 128,
    attentionCount: 23,
    collectProductCount: 15,
    readCount: 89,
    couponCount: 5,
  })
  router.push((route.query.redirect as string) || '/')
}
</script>

<template>
  <div class="min-h-[65vh] flex items-center justify-center py-10">
    <div class="w-full max-w-[420px]">
      <!-- 登录卡片 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <!-- 标题 -->
        <div class="text-center mb-8">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">欢迎登录</h1>
          <p class="text-sm text-gray-500 mt-2">登录后即可享受完整购物体验</p>
        </div>

        <!-- 登录表单 -->
        <form class="space-y-5" @submit.prevent="handleLogin">
          <!-- 用户名 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              用户名 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.username"
              type="text"
              placeholder="请输入用户名（2-20位）"
              :class="[
                'w-full h-12 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2',
                errors.username
                  ? 'border-red-300 focus:ring-red-200 bg-red-50/30'
                  : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
              ]"
              @input="clearError('username')"
            />
            <p v-if="errors.username" class="text-xs text-red-500 mt-1.5 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
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
              placeholder="请输入密码（6-20位）"
              :class="[
                'w-full h-12 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2',
                errors.password
                  ? 'border-red-300 focus:ring-red-200 bg-red-50/30'
                  : 'border-gray-300 focus:ring-red-500 focus:border-transparent',
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

          <!-- 记住我 + 忘记密码 -->
          <div class="flex items-center justify-between text-sm">
            <label class="flex items-center gap-2 text-gray-600 cursor-pointer">
              <input type="checkbox" class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500" />
              <span>记住我</span>
            </label>
            <button type="button" class="text-red-600 hover:text-red-700 font-medium">忘记密码？</button>
          </div>

          <!-- 登录按钮 -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full h-12 bg-red-600 text-white font-bold text-base rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md shadow-red-200"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </button>
        </form>

        <!-- 分隔线 -->
        <div class="flex items-center gap-4 my-6">
          <div class="flex-1 h-px bg-gray-200" />
          <span class="text-xs text-gray-400">或</span>
          <div class="flex-1 h-px bg-gray-200" />
        </div>

        <!-- Mock 快速登录提示 -->
        <div class="text-center text-xs text-gray-400 mb-4">
          演示模式：输入任意用户名和密码即可登录
        </div>

        <!-- 底部链接 -->
        <div class="text-center text-sm">
          <span class="text-gray-500">还没有账号？</span>
          <button class="text-red-600 hover:text-red-700 font-medium ml-1" @click="$router.push('/register')">
            立即注册
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
