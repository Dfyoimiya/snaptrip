import type { App, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'

type PermissionValue = string | string[]

function hasPermission(value: PermissionValue): boolean {
  const required = Array.isArray(value) ? value : [value]
  const granted = useUserStore().permissions
  return granted.includes('*') || required.some((permission) => granted.includes(permission))
}

export function setupPermissionDirective(app: App): void {
  app.directive('permission', {
    mounted(element: HTMLElement, binding: DirectiveBinding<PermissionValue>) {
      if (!hasPermission(binding.value)) {
        element.remove()
      }
    },
  })
}
