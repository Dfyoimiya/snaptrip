import { onBeforeMount, onBeforeUnmount } from 'vue'
import { useAppStore } from '@/stores/app'

const WIDTH = 992 // 响应式断点

/** 判断是否为移动端 */
function isMobile(): boolean {
  const rect = document.body.getBoundingClientRect()
  return rect.width - 1 < WIDTH
}

/** 响应式处理 Composable */
export default function useResizeHandler() {
  const appStore = useAppStore()

  /** 窗口大小变化处理 */
  function resizeHandler() {
    const isMobileDevice = isMobile()
    if (isMobileDevice) {
      appStore.toggleDevice('mobile')
      appStore.closeSidebar(true)
    } else {
      appStore.toggleDevice('desktop')
      appStore.openSidebar()
    }
  }

  onBeforeMount(() => {
    resizeHandler()
    window.addEventListener('resize', resizeHandler)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', resizeHandler)
  })
}
