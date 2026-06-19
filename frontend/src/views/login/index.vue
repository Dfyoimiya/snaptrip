<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Hide, Lock, Message, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loginForm = reactive({
  username: 'admin@snaptrip.com',
  password: 'admin123',
  remember: true,
})
const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const showPassword = ref(false)
const isTyping = ref(false)
const purpleBlinking = ref(false)
const blackBlinking = ref(false)
const mouse = reactive({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
const stageRef = ref<HTMLElement>()

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
}

const passwordActive = computed(() => loginForm.password.length > 0)
const charactersWatching = computed(() => passwordActive.value && showPassword.value)
const eyeTransform = computed(() => {
  if (charactersWatching.value) return 'translate(-4px, -3px)'
  if (isTyping.value) return 'translate(3px, 2px)'
  const rect = stageRef.value?.getBoundingClientRect()
  if (!rect) return 'translate(0, 0)'
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  const x = Math.max(-5, Math.min(5, (mouse.x - centerX) / 80))
  const y = Math.max(-4, Math.min(4, (mouse.y - centerY) / 80))
  return `translate(${x}px, ${y}px)`
})
const bodyLean = computed(() => {
  const rect = stageRef.value?.getBoundingClientRect()
  if (!rect || charactersWatching.value) return '0deg'
  const centerX = rect.left + rect.width / 2
  return `${Math.max(-4, Math.min(4, (mouse.x - centerX) / -180))}deg`
})

let purpleTimer: number | undefined
let blackTimer: number | undefined

function scheduleBlink(target: typeof purpleBlinking, timerName: 'purple' | 'black'): void {
  const timer = window.setTimeout(() => {
    target.value = true
    window.setTimeout(() => {
      target.value = false
      scheduleBlink(target, timerName)
    }, 140)
  }, 2800 + Math.random() * 3500)
  if (timerName === 'purple') purpleTimer = timer
  else blackTimer = timer
}

function handleMouseMove(event: MouseEvent): void {
  mouse.x = event.clientX
  mouse.y = event.clientY
}

function resolveLoginRedirect(): string {
  const redirect = typeof route.query.redirect === 'string'
    ? route.query.redirect
    : ''
  const blockedPaths = ['/login', '/403', '/404']

  if (
    !redirect.startsWith('/')
    || redirect.startsWith('//')
    || blockedPaths.some((path) => redirect === path || redirect.startsWith(`${path}?`))
  ) {
    return '/'
  }
  return redirect
}

async function handleLogin(): Promise<void> {
  if (!loginFormRef.value) return
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm)
    ElMessage.success('欢迎回来')
    await router.replace(resolveLoginRedirect())
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
  scheduleBlink(purpleBlinking, 'purple')
  scheduleBlink(blackBlinking, 'black')
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  if (purpleTimer) window.clearTimeout(purpleTimer)
  if (blackTimer) window.clearTimeout(blackTimer)
})
</script>

<template>
  <main class="login-page">
    <section class="character-panel">
      <header class="brand">
        <span class="brand-mark">S</span>
        <span>SnapTrip 管理后台</span>
      </header>

      <div ref="stageRef" class="character-stage">
        <div
          class="character purple"
          :class="{ shy: passwordActive && !showPassword }"
          :style="{ transform: `skewX(${bodyLean})` }"
        >
          <div class="eye-row purple-eyes">
            <span class="eye" :class="{ blink: purpleBlinking }"><i :style="{ transform: eyeTransform }" /></span>
            <span class="eye" :class="{ blink: purpleBlinking }"><i :style="{ transform: eyeTransform }" /></span>
          </div>
          <div v-if="passwordActive && !showPassword" class="hands">
            <span /><span />
          </div>
        </div>

        <div class="character charcoal" :style="{ transform: `skewX(${bodyLean})` }">
          <div class="eye-row charcoal-eyes">
            <span class="eye small" :class="{ blink: blackBlinking }"><i :style="{ transform: eyeTransform }" /></span>
            <span class="eye small" :class="{ blink: blackBlinking }"><i :style="{ transform: eyeTransform }" /></span>
          </div>
        </div>

        <div class="character coral">
          <div class="dot-eyes coral-eyes">
            <i :style="{ transform: eyeTransform }" /><i :style="{ transform: eyeTransform }" />
          </div>
        </div>

        <div class="character yellow">
          <div class="dot-eyes yellow-eyes">
            <i :style="{ transform: eyeTransform }" /><i :style="{ transform: eyeTransform }" />
          </div>
          <span class="mouth" />
        </div>
      </div>

      <footer class="panel-footer">
        <span>智能规划</span><span>本地生活</span><span>高效管理</span>
      </footer>
    </section>

    <section class="form-panel">
      <div class="mobile-brand">
        <span class="brand-mark">S</span>
        <span>SnapTrip 管理后台</span>
      </div>

      <div class="login-card">
        <div class="welcome">
          <span class="eyebrow">企业管理控制台</span>
          <h1>欢迎回来</h1>
          <p>登录 SnapTrip 管理后台，继续管理你的业务。</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          @keyup.enter="handleLogin"
        >
          <el-form-item label="邮箱" prop="username">
            <el-input
              v-model="loginForm.username"
              size="large"
              placeholder="admin@snaptrip.com"
              :prefix-icon="Message"
              autocomplete="username"
              @focus="isTyping = true"
              @blur="isTyping = false"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              size="large"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              autocomplete="current-password"
              @focus="isTyping = true"
              @blur="isTyping = false"
            >
              <template #suffix>
                <el-icon class="password-toggle" @click="showPassword = !showPassword">
                  <Hide v-if="showPassword" />
                  <View v-else />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="form-options">
            <el-checkbox v-model="loginForm.remember">记住账号</el-checkbox>
            <span class="forgot">忘记密码？</span>
          </div>

          <el-button
            type="primary"
            size="large"
            class="login-button"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '正在登录…' : '登录管理后台' }}
          </el-button>
        </el-form>

        <div class="demo-account">
          <span>演示账号</span>
          <code>admin@snaptrip.com</code>
          <code>admin123</code>
        </div>
      </div>

      <p class="copyright">© 2026 SnapTrip · 智能本地生活服务平台</p>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(480px, 1.05fr) minmax(480px, 0.95fr);
  background: #fff;
}

.character-panel {
  position: relative;
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 42px 52px 34px;
  color: #fff;
  background:
    radial-gradient(circle at 76% 18%, rgba(255, 255, 255, 0.16), transparent 24%),
    linear-gradient(145deg, #304156 0%, #263445 58%, #1f2d3d 100%);

  &::before {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 24px 24px;
    content: '';
  }
}

.brand, .mobile-brand {
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 18px;
  font-weight: 700;
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  background: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, .3);
}

.character-stage {
  position: relative;
  z-index: 2;
  align-self: center;
  width: min(570px, 92%);
  height: 440px;
}

.character {
  position: absolute;
  bottom: 0;
  transform-origin: bottom center;
  transition: height .55s ease, transform .2s ease;
}

.purple {
  left: 12%;
  z-index: 1;
  width: 34%;
  height: 400px;
  border-radius: 14px 14px 0 0;
  background: #7657ff;

  &.shy { height: 430px; }
}
.charcoal {
  left: 44%;
  z-index: 2;
  width: 23%;
  height: 310px;
  border-radius: 10px 10px 0 0;
  background: #20242b;
}
.coral {
  left: 0;
  z-index: 3;
  width: 44%;
  height: 205px;
  border-radius: 130px 130px 0 0;
  background: #ff9770;
}
.yellow {
  left: 57%;
  z-index: 4;
  width: 27%;
  height: 245px;
  border-radius: 90px 90px 0 0;
  background: #ead95a;
}

.eye-row, .dot-eyes { position: absolute; display: flex; gap: 30px; }
.purple-eyes { top: 44px; left: 48px; }
.charcoal-eyes { top: 36px; left: 28px; gap: 22px; }
.coral-eyes { top: 92px; left: 84px; }
.yellow-eyes { top: 48px; left: 52px; gap: 25px; }

.eye {
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: #fff;
  transition: height .12s ease;

  &.small { width: 17px; height: 17px; }
  &.blink { height: 2px; margin-top: 9px; }
  i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #20242b;
    transition: transform .1s ease-out;
  }
}

.dot-eyes i {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #20242b;
  transition: transform .1s ease-out;
}

.mouth {
  position: absolute;
  top: 96px;
  left: 42px;
  width: 76px;
  height: 4px;
  border-radius: 4px;
  background: #20242b;
}

.hands {
  position: absolute;
  top: 44px;
  left: 36px;
  display: flex;
  gap: 8px;
  span {
    width: 56px;
    height: 23px;
    border-radius: 20px;
    background: #8c73ff;
    transform: rotate(25deg);
    &:last-child { transform: rotate(-25deg); }
  }
}

.panel-footer {
  z-index: 2;
  display: flex;
  gap: 28px;
  color: rgba(255,255,255,.58);
  font-size: 13px;
}

.form-panel {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 48px;
  background: #fff;
}

.mobile-brand { display: none; color: #303133; }
.login-card { width: min(420px, 100%); }
.welcome {
  margin-bottom: 34px;
  .eyebrow { color: #409eff; font-size: 12px; font-weight: 700; letter-spacing: 1.8px; }
  h1 { margin: 9px 0 8px; color: #1f2937; font-size: 34px; letter-spacing: -1px; }
  p { color: #909399; line-height: 1.7; }
}

:deep(.el-form-item) { margin-bottom: 23px; }
:deep(.el-form-item__label) { color: #303133; font-weight: 600; }
:deep(.el-input__wrapper) {
  min-height: 48px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  box-shadow: none;
  transition: border-color .2s, box-shadow .2s;
  &.is-focus {
    border-color: #409eff;
    box-shadow: 0 0 0 3px rgba(64, 158, 255, .12);
  }
}
.password-toggle { cursor: pointer; color: #909399; }
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -4px 0 24px;
}
.forgot { cursor: pointer; color: #409eff; font-size: 14px; }
.login-button {
  width: 100%;
  height: 49px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  box-shadow: 0 10px 24px rgba(64, 158, 255, .24);
}
.demo-account {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  padding: 13px 15px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  color: #909399;
  background: #f8fafc;
  font-size: 12px;
  code { color: #606266; }
}
.copyright {
  position: absolute;
  bottom: 24px;
  color: #c0c4cc;
  font-size: 12px;
}

@media (max-width: 960px) {
  .login-page { display: block; }
  .character-panel { display: none; }
  .form-panel { padding: 40px 24px; }
  .mobile-brand {
    position: absolute;
    top: 28px;
    left: 28px;
    display: flex;
  }
}
</style>
