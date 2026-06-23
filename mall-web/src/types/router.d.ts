import 'vue-router'

export {}

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requireAuth?: boolean
    guestOnly?: boolean
    fullMain?: boolean
    fillMain?: boolean
  }
}
