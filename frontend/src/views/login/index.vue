<script lang="ts" setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 登录表单
const loginForm = reactive({
  username: 'admin',
  password: '123456',
  remember: false,
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' },
  ],
}

const loginFormRef = ref<FormInstance>()
const loading = ref(false)

/** 处理登录 */
async function handleLogin() {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(loginForm)
        ElMessage.success('登录成功')
        const redirect = route.query.redirect as string
        router.push(redirect || '/')
      } catch (error) {
        console.error('登录失败:', error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<template>
  <div class="login-page">
    <!-- 顶部 Logo -->
    <div class="login-header">
      <div class="logo">
        <img src="/vite.svg" alt="logo" class="logo-img" />
        <span class="logo-text">Mall Admin</span>
      </div>
    </div>

    <div class="login-body">
      <!-- 左侧表单 -->
      <div class="login-form-section">
        <div class="form-container">
          <h1 class="form-title">
            <span class="title-main">登录到</span>
            <span class="title-brand">Mall Admin</span>
          </h1>
          <p class="form-subtitle">
            <span>还没有账号？</span>
            <a href="javascript:void(0)" class="link-primary">注册新账号</a>
          </p>

          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            class="login-form"
            @keyup.enter="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                size="large"
                :prefix-icon="User"
                clearable
                class="login-input"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                clearable
                class="login-input"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="loginForm.remember" size="small">
                记住账号
              </el-checkbox>
              <a href="javascript:void(0)" class="link-forgot">忘记密码？</a>
            </div>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                class="login-btn"
                :loading="loading"
                @click="handleLogin"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-footer">
            <span class="footer-text">其他登录方式</span>
            <div class="divider-line">
              <span class="divider-text">使用手机号登录</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧装饰 -->
      <div class="login-hero-section">
        <div class="hero-image-wrapper">
          <img src="/login-hero.png" alt="hero" class="hero-image" />
        </div>
        <!-- 浮动装饰元素 -->
        <div class="floating-shape shape-1"></div>
        <div class="floating-shape shape-2"></div>
        <div class="floating-shape shape-3"></div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  min-height: 600px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 顶部 Logo */
.login-header {
  flex-shrink: 0;
  padding: 24px 40px;

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;

    .logo-img {
      width: 28px;
      height: 28px;
    }

    .logo-text {
      font-size: 18px;
      font-weight: 700;
      color: #1a1a2e;
      letter-spacing: -0.5px;
    }
  }
}

/* 主体区域 */
.login-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 60px;
  gap: 60px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 左侧表单 */
.login-form-section {
  flex: 0 0 420px;
  display: flex;
  align-items: center;
  justify-content: center;

  .form-container {
    width: 100%;
    max-width: 380px;
  }

  .form-title {
    margin: 0 0 8px;
    font-size: 28px;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.3;
    display: flex;
    flex-direction: column;
    gap: 2px;

    .title-brand {
      color: #1a1a2e;
    }
  }

  .form-subtitle {
    margin: 0 0 32px;
    font-size: 13px;
    color: #8c8c8c;

    .link-primary {
      color: #0052d9;
      text-decoration: none;
      margin-left: 4px;
      font-weight: 500;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .login-form {
    .login-input {
      :deep(.el-input__wrapper) {
        background-color: #f5f6fa;
        border-radius: 8px;
        box-shadow: none !important;
        padding: 4px 12px;
        border: 1px solid transparent;
        transition: all 0.3s;

        &:hover,
        &.is-focus {
          border-color: #0052d9;
          background-color: #ffffff;
          box-shadow: 0 0 0 3px rgba(0, 82, 217, 0.08) !important;
        }

        input {
          font-size: 14px;
          color: #1a1a2e;

          &::placeholder {
            color: #b0b3c7;
          }
        }
      }
    }

    .form-options {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      margin-top: -4px;

      :deep(.el-checkbox__label) {
        font-size: 13px;
        color: #666;
      }

      .link-forgot {
        font-size: 13px;
        color: #0052d9;
        text-decoration: none;
        font-weight: 500;

        &:hover {
          text-decoration: underline;
        }
      }
    }

    .login-btn {
      width: 100%;
      height: 44px;
      font-size: 15px;
      font-weight: 600;
      letter-spacing: 2px;
      border-radius: 8px;
      background: linear-gradient(135deg, #0052d9 0%, #3370ff 100%);
      border: none;
      box-shadow: 0 4px 14px rgba(0, 82, 217, 0.35);
      transition: all 0.3s;

      &:hover {
        background: linear-gradient(135deg, #0048c0 0%, #2a65f5 100%);
        box-shadow: 0 6px 20px rgba(0, 82, 217, 0.45);
        transform: translateY(-1px);
      }

      &:active {
        transform: translateY(0);
      }
    }
  }

  .form-footer {
    margin-top: 24px;
    text-align: center;

    .footer-text {
      font-size: 13px;
      color: #b0b3c7;
      display: block;
      margin-bottom: 12px;
    }

    .divider-line {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        top: 50%;
        height: 1px;
        background: #e8e9f0;
      }

      .divider-text {
        position: relative;
        z-index: 1;
        background: #fff;
        padding: 0 16px;
        font-size: 13px;
        color: #8c8c8c;
        cursor: pointer;

        &:hover {
          color: #0052d9;
        }
      }
    }
  }
}

/* 右侧装饰 */
.login-hero-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  min-height: 500px;

  .hero-image-wrapper {
    position: relative;
    z-index: 2;
    width: 100%;
    max-width: 500px;

    .hero-image {
      width: 100%;
      height: auto;
      object-fit: contain;
    }
  }

  /* 浮动装饰形状 */
  .floating-shape {
    position: absolute;
    border-radius: 50%;
    opacity: 0.15;
    z-index: 1;

    &.shape-1 {
      width: 300px;
      height: 300px;
      background: linear-gradient(135deg, #0052d9, #3370ff);
      top: 10%;
      right: 5%;
      filter: blur(60px);
      animation: float 8s ease-in-out infinite;
    }

    &.shape-2 {
      width: 200px;
      height: 200px;
      background: linear-gradient(135deg, #00c853, #69f0ae);
      bottom: 15%;
      left: 10%;
      filter: blur(50px);
      animation: float 10s ease-in-out infinite 2s;
    }

    &.shape-3 {
      width: 150px;
      height: 150px;
      background: linear-gradient(135deg, #7c4dff, #b388ff);
      top: 40%;
      left: 0;
      filter: blur(40px);
      animation: float 7s ease-in-out infinite 1s;
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-20px) scale(1.05);
  }
}

/* 响应式 */
@media screen and (max-width: 900px) {
  .login-hero-section {
    display: none;
  }

  .login-form-section {
    flex: 1;
  }
}

@media screen and (max-width: 480px) {
  .login-header {
    padding: 16px 20px;
  }

  .login-body {
    padding: 0 20px;
  }

  .form-title {
    font-size: 24px !important;
  }
}
</style>
