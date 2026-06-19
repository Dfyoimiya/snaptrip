import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { setupRouterGuard } from './router/guard'
import { setupPermissionDirective } from './directives/permission'
import { useAppStore } from '@/stores/app'

// 导入全局样式
import '@/styles/index.scss'

// 创建应用
const app = createApp(App)

// 注册 Element Plus
app.use(ElementPlus, { locale: zhCn })

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 使用插件
const pinia = createPinia()
app.use(pinia)
app.use(router)
setupPermissionDirective(app)

useAppStore(pinia).applyTheme()

// 配置路由守卫
setupRouterGuard(router)

// 挂载应用
app.mount('#app')
