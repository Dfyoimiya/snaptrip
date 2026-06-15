<script setup lang="ts">
/**
 * ============================================
 * 浏览历史页 (MemberHistoryView)
 *
 * NOTE: 后端暂未提供浏览历史 API。
 * 当前显示空状态占位，待后端接口就绪后可接入。
 * ============================================
 */
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <div class="px-6 py-4 border-b border-gray-100">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-bold text-gray-900">浏览足迹</h2>
      </div>
    </div>

    <div class="flex flex-col items-center justify-center py-20 text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-base font-medium">浏览历史功能即将上线</p>
      <p class="text-sm mt-1">您浏览过的商品将会显示在这里</p>
    </div>
  </div>
</template>
