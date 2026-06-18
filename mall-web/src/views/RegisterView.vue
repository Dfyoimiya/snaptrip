<script setup lang="ts">
/**
 * ============================================
 * 注册页面 (RegisterView)
 * ============================================
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registerAPI } from '@/apis/member'
import { useMemberStore } from '@/stores/member'

const router = useRouter()
const route = useRoute()
const memberStore = useMemberStore()

const form = ref({
  email: '',
  password: '',
  confirmPassword: '',
})
const errors = ref<Record<string, string>>({})
const loading = ref(false)

const validateForm = (): boolean => {
  const errs: Record<string, string> = {}

  if (!form.value.email) {
    errs.email = '请输入邮箱'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    errs.email = '请输入有效的邮箱地址'
  }

  if (!form.value.password) {
    errs.password = '请输入密码'
  } else if (form.value.password.length < 6 || form.value.password.length > 128) {
    errs.password = '密码长度应为6-128位'
  }

  if (!form.value.confirmPassword) {
    errs.confirmPassword = '请确认密码'
  } else if (form.value.password !== form.value.confirmPassword) {
    errs.confirmPassword = '两次输入的密码不一致'
  }

  errors.value = errs
  return Object.keys(errs).length === 0
}

const clearError = (field: string) => {
  delete errors.value[field]
}

const handleRegister = async () => {
  if (!validateForm()) return
  loading.value = true
  errors.value = {}

  try {
    await registerAPI({
      email: form.value.email,
      password: form.value.password,
    })
    router.push('/login')
  } catch (e: any) {
    errors.value.general = e?.message || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[65vh] flex items-center justify-center py-10">
    <div class="w-full max-w-[420px]">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div class="text-center mb-8">
          <div class="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">创建账号</h1>
          <p class="text-sm text-gray-500 mt-2">注册后即可开始购物</p>
        </div>

        <form class="space-y-4" @submit.prevent="handleRegister">
          <div v-if="errors.general" class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            {{ errors.general }}
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              邮箱 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.email"
              type="email"
              placeholder="请输入邮箱地址"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.email ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-brand-500']"
              @input="clearError('email')"
            />
            <p v-if="errors.email" class="text-xs text-red-500 mt-1">{{ errors.email }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              密码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              placeholder="6-128位"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.password ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-brand-500']"
              @input="clearError('password')"
            />
            <p v-if="errors.password" class="text-xs text-red-500 mt-1">{{ errors.password }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">
              确认密码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              :class="['w-full h-11 px-4 border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2', errors.confirmPassword ? 'border-red-300 focus:ring-red-200 bg-red-50/30' : 'border-gray-300 focus:ring-brand-500']"
              @input="clearError('confirmPassword')"
            />
            <p v-if="errors.confirmPassword" class="text-xs text-red-500 mt-1">{{ errors.confirmPassword }}</p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full h-12 bg-brand-600 text-white font-bold text-base rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md shadow-brand-200"
          >
            {{ loading ? '注册中...' : '注 册' }}
          </button>
        </form>

        <div class="mt-6 text-center text-sm">
          <span class="text-gray-500">已有账号？</span>
          <button class="text-brand-600 hover:text-brand-700 font-medium ml-1" @click="$router.push('/login')">
            去登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
