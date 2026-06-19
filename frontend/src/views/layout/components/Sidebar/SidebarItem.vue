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
  const showingChildren = children.filter((child: any) => !child.hidden)

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
          <component :is="getIcon((onlyOneChild.meta?.icon || item.meta?.icon || 'Document') as string)" />
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
      v-for="child in item.children?.filter((route) => !route.hidden)"
      :key="child.path"
      :item="child"
      :base-path="resolvePath(child.path)"
      is-nest
    />
  </el-sub-menu>
</template>

<style lang="scss" scoped>
.menu-title {
  overflow: hidden;
  margin-left: 3px;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
}

:deep(.el-menu-item) {
  height: 40px;
  margin: 2px 0;
  padding: 0 11px !important;
  border-radius: 8px;
  color: var(--admin-text-secondary);
  line-height: 40px;
  transition: color .18s ease, background .18s ease;

  .el-icon {
    color: var(--admin-text-muted);
    font-size: 17px;
  }

  &:hover {
    color: var(--admin-text);
    background: var(--admin-hover) !important;
  }

  &.is-active {
    color: #1677ff;
    background: #edf5ff !important;
    font-weight: 600;

    .el-icon { color: #409eff; }
  }
}

:deep(.el-sub-menu__title) {
  height: 40px;
  margin: 2px 0;
  padding: 0 11px !important;
  border-radius: 8px;
  color: var(--admin-text-secondary);
  line-height: 40px;

  .el-icon { color: var(--admin-text-muted); font-size: 17px; }

  &:hover {
    color: var(--admin-text);
    background: var(--admin-hover) !important;
  }
}

:deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #1677ff;
  .el-icon { color: #409eff; }
}

:deep(.el-menu--inline) {
  padding-left: 8px;
  background: transparent;
}

:global(.sidebar-popper-white) {
  background: var(--admin-surface) !important;
  border: 1px solid var(--admin-border) !important;
  border-radius: 9px !important;
  box-shadow: 0 12px 30px rgba(15, 23, 42, .12) !important;

  .el-menu { padding: 5px !important; background: var(--admin-surface) !important; }

  .el-menu-item {
    height: 36px !important;
    margin: 2px 0;
    border-radius: 7px;
    color: var(--admin-text-secondary) !important;
    line-height: 36px !important;
    &:hover { background: var(--admin-hover) !important; }
    &.is-active {
      color: #1677ff !important;
      background: #edf5ff !important;
    }
  }
}
</style>
