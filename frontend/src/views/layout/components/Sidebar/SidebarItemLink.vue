<script lang="ts" setup>
import { computed } from 'vue'

const props = defineProps<{
  to: string
}>()

/** 判断是否为外部链接 */
const isExternal = computed(() => {
  return typeof props.to === 'string' && props.to.startsWith('http')
})

/** 外部链接属性 */
const linkAttrs = computed(() => {
  if (isExternal.value) {
    return {
      href: props.to,
      target: '_blank',
      rel: 'noopener noreferrer',
    }
  }
  return {}
})
</script>

<template>
  <!-- 外部链接 -->
  <a v-if="isExternal" v-bind="linkAttrs" class="sidebar-link">
    <slot />
  </a>
  <!-- 内部路由 -->
  <router-link v-else :to="to" class="sidebar-link">
    <slot />
  </router-link>
</template>

<style lang="scss" scoped>
.sidebar-link {
  display: block;
  text-decoration: none;
}
</style>
