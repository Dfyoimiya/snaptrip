<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="forbidden-page">
    <div class="status-code">403</div>
    <h1>暂无访问权限</h1>
    <p>当前账号没有访问该页面的权限，请联系管理员分配角色。</p>
    <el-button type="primary" @click="router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 16px;
  color: #606266;
  background: #f5f7fa;
}
.status-code { color: #409eff; font-size: 96px; font-weight: 700; line-height: 1; }
h1 { color: #303133; font-size: 24px; }
</style>
