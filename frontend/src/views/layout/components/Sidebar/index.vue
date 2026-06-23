<script lang="ts" setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'
import { useUserStore } from '@/stores/user'
import SidebarItem from './SidebarItem.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const permissionStore = usePermissionStore()
const userStore = useUserStore()

const sidebar = computed(() => appStore.sidebar)
const device = computed(() => appStore.device)
const isMobileDevice = computed(() => device.value === 'mobile')
const displayName = computed(
  () => userStore.userInfo.nickname || userStore.userInfo.username || '管理员',
)
const userInitial = computed(() => displayName.value.slice(0, 1).toUpperCase())

const activeMenu = computed(() => {
  const { meta, path } = route
  return (meta?.activeMenu as string) || path
})

const menuRoutes = computed(() => {
  return permissionStore.routers.filter((item) => !item.hidden && item.meta)
})

function handleWorkspaceCommand(command: string): void {
  if (command === 'members') router.push('/ums/admin')
  if (command === 'roles') router.push('/ums/role')
  if (command === 'settings') router.push('/setting/oss')
}

async function handleAccountCommand(command: string): Promise<void> {
  if (command === 'home') {
    await router.push('/home')
  }
  if (command === 'logout') {
    await userStore.logout()
    await router.replace('/login')
  }
}
</script>

<template>
  <aside
    class="sidebar-wrapper"
    :class="{
      'sidebar-open': sidebar.opened,
      'no-animation': sidebar.withoutAnimation,
    }"
  >
    <div class="brand-row">
      <router-link to="/home" class="brand-link">
        <span class="brand-mark">S</span>
        <span class="brand-name">SnapTrip</span>
      </router-link>
      <button
        v-if="isMobileDevice"
        class="close-button"
        type="button"
        aria-label="关闭侧边栏"
        @click.stop="appStore.closeSidebar(false)"
      >
        <el-icon><Close /></el-icon>
      </button>
    </div>

    <div class="workspace-row">
      <el-dropdown
        trigger="click"
        placement="bottom-start"
        popper-class="sidebar-workspace-dropdown"
        @command="handleWorkspaceCommand"
      >
        <button class="workspace-trigger" type="button">
          <span class="workspace-avatar">ST</span>
          <span class="workspace-copy">
            <strong>SnapTrip 商务管理</strong>
            <small>管理工作区</small>
          </span>
          <el-icon class="workspace-chevron"><ArrowUpBold /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="members">
              <el-icon><UserFilled /></el-icon>成员管理
            </el-dropdown-item>
            <el-dropdown-item command="roles">
              <el-icon><Key /></el-icon>角色与权限
            </el-dropdown-item>
            <el-dropdown-item command="settings" divided>
              <el-icon><Setting /></el-icon>系统设置
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="menu-caption">工作台</div>

    <el-scrollbar class="sidebar-scroll">
      <el-menu
        :default-active="activeMenu"
        :collapse="false"
        :collapse-transition="false"
        :unique-opened="true"
        mode="vertical"
        router
      >
        <SidebarItem
          v-for="item in menuRoutes"
          :key="item.path"
          :item="item"
          :base-path="item.path"
        />
      </el-menu>
    </el-scrollbar>

    <div class="sidebar-bottom">
      <router-link to="/setting/oss" class="bottom-link" title="系统设置">
        <el-icon><Setting /></el-icon>
        <span>系统设置</span>
      </router-link>

      <el-dropdown
        trigger="click"
        placement="top-start"
        popper-class="sidebar-account-dropdown"
        @command="handleAccountCommand"
      >
        <button class="account-trigger" type="button">
          <el-avatar :size="28" :src="userStore.avatar">
            {{ userInitial }}
          </el-avatar>
          <span class="account-copy">
            <strong>{{ displayName }}</strong>
            <small>{{ userStore.userInfo.username }}</small>
          </span>
          <el-icon class="account-chevron"><MoreFilled /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <div class="account-summary">
              <el-avatar :size="48" :src="userStore.avatar">{{ userInitial }}</el-avatar>
              <span class="account-summary-copy">
                <strong>{{ displayName }}</strong>
                <small>{{ userStore.userInfo.username }}</small>
              </span>
            </div>
            <el-dropdown-item command="home" divided>
              <el-icon><User /></el-icon>个人账户
            </el-dropdown-item>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>退出账户
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
.sidebar-wrapper {
  position: fixed;
  top: 12px;
  left: 12px;
  bottom: 12px;
  z-index: 50;
  display: flex;
  width: 184px;
  height: calc(100vh - 24px);
  flex-direction: column;
  overflow: hidden;
  color: var(--admin-text-secondary);
  background: var(--glass-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
  transform: translateX(calc(-100% - 12px));
  opacity: 0;
  pointer-events: none;
  transition:
    transform 0.25s ease,
    opacity 0.2s ease;

  &.sidebar-open {
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
  }

  &.no-animation {
    transition: none !important;
  }
}

.brand-row {
  display: flex;
  height: 48px;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  border-bottom: 1px solid var(--admin-border);
}

.brand-link {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  color: var(--admin-text);
  text-decoration: none;
}

.brand-mark, .workspace-avatar {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #337ecc);
  font-weight: 800;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  box-shadow: 0 6px 16px rgba(64, 158, 255, .24);
}

.brand-name {
  white-space: nowrap;
  font-size: 15px;
  font-weight: 750;
  letter-spacing: -.3px;
}

.close-button {
  display: grid;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  cursor: pointer;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: #9ca3af;
  background: transparent;
  transition: .18s ease;

  &:hover { color: #409eff; background: var(--admin-hover); }
}

.workspace-row { padding: 8px 6px 4px; }
.workspace-trigger {
  display: flex;
  width: 100%;
  height: 44px;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 6px;
  border: 0;
  border-radius: 9px;
  color: var(--admin-text);
  background: transparent;
  text-align: left;
  transition: background .18s ease;

  &:hover { background: var(--admin-hover); }
}
.workspace-avatar {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  font-size: 10px;
}
.workspace-copy, .account-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  line-height: 1.25;

  strong { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 12px; }
  small { overflow: hidden; margin-top: 2px; color: #9ca3af; white-space: nowrap; text-overflow: ellipsis; font-size: 10px; }
}
.workspace-chevron, .account-chevron { flex-shrink: 0; color: #b4bac4; font-size: 11px; }

.menu-caption {
  padding: 8px 14px 4px;
  color: #b0b6c0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.sidebar-scroll {
  flex: 1;
  overflow: hidden;
  padding: 0 6px;

  :deep(.el-scrollbar__wrap) { overflow-x: hidden !important; }
  :deep(.el-menu) {
    width: 100%;
    border-right: 0;
    background: transparent;
  }
}

.sidebar-bottom {
  flex-shrink: 0;
  padding: 6px;
  border-top: 1px solid var(--admin-border);
}

.bottom-link, .account-trigger {
  display: flex;
  width: 100%;
  height: 38px;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  padding: 0 8px;
  border: 0;
  border-radius: 8px;
  color: #667085;
  background: transparent;
  text-decoration: none;
  transition: .18s ease;

  &:hover { color: #409eff; background: var(--admin-hover); }
  .el-icon { flex-shrink: 0; font-size: 16px; }
}
.account-trigger { height: 44px; margin-top: 2px; text-align: left; }

:global(.sidebar-workspace-dropdown),
:global(.sidebar-account-dropdown) {
  min-width: 210px;
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  box-shadow: 0 12px 32px rgba(15, 23, 42, .12) !important;
}

:global(.sidebar-account-dropdown) {
  width: 240px;
}

:global(.sidebar-account-dropdown .el-dropdown-menu) {
  padding: 6px 0;
}

:global(.sidebar-account-dropdown .account-summary) {
  display: flex;
  width: 100%;
  box-sizing: border-box;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 14px 16px 16px;
  text-align: center;
}

:global(.sidebar-account-dropdown .account-summary-copy) {
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  align-items: center;
}

:global(.sidebar-account-dropdown .account-summary-copy strong),
:global(.sidebar-account-dropdown .account-summary-copy small) {
  display: block;
  overflow: hidden;
  width: 100%;
  white-space: nowrap;
  text-align: center;
  text-overflow: ellipsis;
}

:global(.sidebar-account-dropdown .account-summary-copy strong) {
  color: var(--admin-text);
  font-size: 14px;
  line-height: 20px;
}

:global(.sidebar-account-dropdown .account-summary-copy small) {
  margin-top: 3px;
  color: #909399;
  font-size: 11px;
  line-height: 16px;
}

/* ========== Mobile: drawer overlay ========== */
@media (max-width: 991px) {
  .sidebar-wrapper {
    top: 0;
    left: 0;
    bottom: 0;
    width: 240px;
    height: 100vh;
    border-radius: 0;
    border: none;
    border-right: 1px solid var(--admin-border);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    box-shadow: 12px 0 32px rgba(15, 23, 42, 0.18);
    transform: translateX(-100%);
    opacity: 1;
    transition: transform 0.25s ease;
    z-index: 999;
    pointer-events: none;

    &.sidebar-open {
      transform: translateX(0);
      pointer-events: auto;
    }

    &.no-animation {
      transition: none !important;
    }

    .brand-row {
      height: 56px;
      padding: 0 12px;
    }

    .brand-mark {
      width: 32px;
      height: 32px;
    }

    .brand-name {
      font-size: 16px;
    }

    .workspace-row { padding: 10px 8px 6px; }
    .workspace-trigger {
      height: 48px;
      padding: 6px 8px;
      gap: 10px;
    }
    .workspace-avatar {
      width: 30px;
      height: 30px;
    }
    .workspace-copy strong { font-size: 13px; }
    .workspace-copy small { font-size: 11px; }

    .menu-caption {
      padding: 10px 16px 6px;
    }

    .sidebar-scroll {
      padding: 0 8px;
    }

    .sidebar-bottom {
      padding: 8px;
    }

    .bottom-link, .account-trigger {
      height: 40px;
      padding: 0 10px;
      gap: 11px;

      .el-icon { font-size: 17px; }
    }
    .account-trigger { height: 48px; margin-top: 4px; }
  }
}

/* ========== Dark mode ========== */
html.dark {
  .sidebar-wrapper {
    background: var(--glass-bg);
  }

  .workspace-chevron, .account-chevron {
    color: #6b7280;
  }

  .workspace-copy small, .account-copy small {
    color: #6b7280;
  }
}
</style>
