import { defineStore } from 'pinia'
import { reactive, computed, ref } from 'vue'

/** 设备类型 */
export type DeviceType = 'desktop' | 'mobile'

/** 侧边栏状态 */
interface SidebarState {
  opened: boolean
  withoutAnimation: boolean
}

export const useAppStore = defineStore('app', () => {
  // State
  const sidebar = reactive<SidebarState>({
    opened: true,
    withoutAnimation: false,
  })
  const device = ref<DeviceType>('desktop')
  const fixedHeader = ref(true)

  // Getters
  const sidebarOpened = computed(() => sidebar.opened)

  // Actions
  /** 切换侧边栏展开/收起 */
  function toggleSidebar() {
    sidebar.opened = !sidebar.opened
    sidebar.withoutAnimation = false
  }

  /** 关闭侧边栏 */
  function closeSidebar(withoutAnimation: boolean = false) {
    sidebar.opened = false
    sidebar.withoutAnimation = withoutAnimation
  }

  /** 打开侧边栏 */
  function openSidebar() {
    sidebar.opened = true
    sidebar.withoutAnimation = false
  }

  /** 切换设备类型 */
  function toggleDevice(val: DeviceType) {
    device.value = val
  }

  return {
    sidebar,
    device,
    fixedHeader,
    sidebarOpened,
    toggleSidebar,
    closeSidebar,
    openSidebar,
    toggleDevice,
  }
})
