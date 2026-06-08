<script lang="ts" setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'
import SidebarItem from './SidebarItem.vue'

const route = useRoute()
const appStore = useAppStore()
const permissionStore = usePermissionStore()

const sidebar = computed(() => appStore.sidebar)
const device = computed(() => appStore.device)
const isCollapse = computed(() => !sidebar.value.opened)

const activeMenu = computed(() => {
  const { meta, path } = route
  if (meta?.activeMenu) return meta.activeMenu as string
  return path
})

const menuRoutes = computed(() => {
  return permissionStore.routers.filter((r) => !r.hidden && r.meta)
})

function handleClickOutside() {
  if (device.value === 'mobile' && sidebar.value.opened) {
    appStore.closeSidebar(false)
  }
}
</script>

<template>
  <div class="sidebar-wrapper">
    <!-- Logo -->
    <div class="sidebar-logo" :class="{ collapse: isCollapse }">
      <router-link to="/" class="logo-link">
        <img src="/vite.svg" class="logo-img" alt="logo" />
        <h1 v-show="!isCollapse" class="logo-title">Mall Admin</h1>
      </router-link>
    </div>

    <!-- Menu -->
    <el-scrollbar class="sidebar-scroll">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        :unique-opened="true"
        mode="vertical"
        router
      >
        <SidebarItem
          v-for="r in menuRoutes"
          :key="r.path"
          :item="r"
          :base-path="r.path"
        />
      </el-menu>
    </el-scrollbar>

    <!-- 底部折叠按钮 -->
    <div class="sidebar-footer" @click="appStore.toggleSidebar">
      <el-icon :size="14">
        <Fold v-if="sidebar.opened" />
        <Expand v-else />
      </el-icon>
    </div>

    <!-- 移动端遮罩 -->
    <div
      v-if="device === 'mobile' && sidebar.opened"
      class="drawer-bg"
      @click="handleClickOutside"
    />
  </div>
</template>

<style lang="scss" scoped>
.sidebar-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #fff;
  border-right: 1px solid #f0f0f0;
  box-shadow: 2px 0 8px rgba(29, 35, 41, 0.05);
  position: relative;
  z-index: 200;

  .sidebar-logo {
    flex-shrink: 0;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    border-bottom: 1px solid #f0f0f0;
    overflow: hidden;

    .logo-link {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      height: 100%;
      width: 100%;

      .logo-img {
        width: 28px;
        height: 28px;
        flex-shrink: 0;
      }

      .logo-title {
        margin: 0;
        font-size: 16px;
        font-weight: 700;
        color: #1f2229;
        white-space: nowrap;
        letter-spacing: -0.3px;
      }
    }
  }

  .sidebar-scroll {
    flex: 1;
    overflow: hidden;

    :deep(.el-scrollbar__wrap) {
      overflow-x: hidden !important;
    }

    :deep(.el-menu) {
      border-right: none;
      background: transparent;

      // 选中项蓝色左边框
      .el-menu-item.is-active {
        color: #165dff;
        background-color: #f2f3f5;
        border-right: 3px solid #165dff;
        font-weight: 600;

        .el-icon {
          color: #165dff;
        }
      }

      .el-menu-item:hover {
        background-color: #f2f3f5;
        color: #1f2229;
      }

      .el-sub-menu {
        .el-sub-menu__title:hover {
          background-color: #f2f3f5;
          color: #1f2229;
        }

        &.is-active .el-sub-menu__title {
          color: #165dff;
          font-weight: 600;

          .el-icon {
            color: #165dff;
          }
        }
      }
    }
  }

  .sidebar-footer {
    flex-shrink: 0;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-top: 1px solid #f0f0f0;
    cursor: pointer;
    color: #86909c;
    transition: all 0.2s;

    &:hover {
      background: #f2f3f5;
      color: #165dff;
    }
  }
}

/* 收起状态 */
:global(.hideSidebar) .sidebar-wrapper {
  .sidebar-logo {
    padding: 0;
    justify-content: center;

    .logo-link {
      justify-content: center;
    }
  }
}

/* 移动端遮罩 */
.drawer-bg {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 198;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
}
</style>
