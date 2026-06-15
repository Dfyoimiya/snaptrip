<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-8xl font-bold text-gray-200 mb-4">404</h1>
      <p class="text-xl text-gray-500 mb-8">抱歉，您访问的页面不存在</p>
      <button
        class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        @click="router.push('/')"
      >
        返回首页
      </button>
    </div>
  </div>
</template>
