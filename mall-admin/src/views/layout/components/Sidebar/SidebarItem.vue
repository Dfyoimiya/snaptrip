<script lang="ts" setup>
import { computed } from 'vue'
import type { RouteRecordExt } from '@/types'
import SidebarItemLink from './SidebarItemLink.vue'

const props = defineProps<{
  item: RouteRecordExt
  basePath: string
  isNest?: boolean
}>()

const onlyOneChild = computed(() => {
  const children = props.item.children || []
  const showingChildren = children.filter((child) => !child.hidden)

  if (showingChildren.length === 1) {
    return showingChildren[0]
  }
  if (showingChildren.length === 0) {
    return { ...props.item, path: '', noShowingChildren: true }
  }
  return null
})

const alwaysShow = computed(() => {
  return props.item.meta?.alwaysShow || props.item.alwaysShow
})

function resolvePath(routePath: string): string {
  if (routePath.startsWith('http')) return routePath
  if (routePath.startsWith('/')) return routePath
  const base = props.basePath
  if (base.endsWith('/')) return base + routePath
  if (routePath === '') return base
  return base + '/' + routePath
}

function getIcon(iconName: string): string {
  return iconName || 'Document'
}
</script>

<template>
  <!-- 单个子路由 -->
  <template v-if="onlyOneChild && !alwaysShow">
    <SidebarItemLink :to="resolvePath(onlyOneChild.path)" v-if="onlyOneChild.meta">
      <el-menu-item :index="resolvePath(onlyOneChild.path)" :class="{ 'submenu-title-noDropdown': !isNest }">
        <el-icon :size="16">
          <component :is="getIcon(onlyOneChild.meta?.icon || item.meta?.icon || 'Document')" />
        </el-icon>
        <template #title>
          <span class="menu-title">{{ onlyOneChild.meta?.title || item.meta?.title }}</span>
        </template>
      </el-menu-item>
    </SidebarItemLink>
  </template>

  <!-- 多个子路由 -->
  <el-sub-menu v-else :index="resolvePath(item.path)" popper-class="sidebar-popper-white">
    <template #title>
      <el-icon v-if="item.meta?.icon" :size="16">
        <component :is="getIcon(item.meta?.icon)" />
      </el-icon>
      <span class="menu-title">{{ item.meta?.title }}</span>
    </template>

    <SidebarItem
      v-for="child in item.children"
      :key="child.path"
      :item="child"
      :base-path="resolvePath(child.path)"
      is-nest
    />
  </el-sub-menu>
</template>

<style lang="scss" scoped>
.menu-title {
  font-size: 14px;
  margin-left: 2px;
}

/* 白色风格菜单项 */
:deep(.el-menu-item) {
  height: 42px;
  line-height: 42px;
  color: #4e5969;
  border-right: 3px solid transparent;

  .el-icon {
    color: #86909c;
  }

  &:hover {
    background-color: #f2f3f5 !important;
    color: #1f2229;
  }

  &.is-active {
    color: #165dff;
    background-color: #f2f3f5 !important;
    border-right-color: #165dff;
    font-weight: 600;

    .el-icon {
      color: #165dff;
    }
  }
}

:deep(.el-sub-menu__title) {
  height: 42px;
  line-height: 42px;
  color: #4e5969;

  .el-icon {
    color: #86909c;
  }

  &:hover {
    background-color: #f2f3f5 !important;
    color: #1f2229;
  }
}

/* 弹出菜单白色风格 */
:global(.sidebar-popper-white) {
  background: #fff !important;
  border: 1px solid #e5e6eb !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;

  .el-menu {
    background: #fff !important;
  }

  .el-menu-item {
    color: #4e5969 !important;
    height: 38px !important;
    line-height: 38px !important;

    &:hover {
      background-color: #f2f3f5 !important;
    }

    &.is-active {
      color: #165dff !important;
      background-color: #f2f3f5 !important;
    }
  }
}
</style>
