<script lang="ts" setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}

function goBack() {
  router.back()
}
</script>

<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <div class="error-code">404</div>
      <div class="error-divider" />
      <h2 class="error-title">页面不存在</h2>
      <p class="error-desc">
        抱歉，您访问的页面不存在或已被移除。
      </p>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goBack">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.not-found-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f2f5;

  .not-found-content {
    text-align: center;
    padding: 40px;

    .error-code {
      font-size: 160px;
      font-weight: 700;
      color: #409eff;
      line-height: 1;
      letter-spacing: -8px;
      text-shadow: 0 4px 20px rgba(64, 158, 255, 0.3);
    }

    .error-divider {
      width: 60px;
      height: 4px;
      background: #409eff;
      margin: 24px auto;
      border-radius: 2px;
    }

    .error-title {
      font-size: 24px;
      color: #1a1f3c;
      margin: 0 0 12px;
    }

    .error-desc {
      font-size: 14px;
      color: #909399;
      margin: 0 0 24px;
    }

    .error-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
    }
  }
}
</style>
