/**
 * ============================================
 * 路由配置
 * 包含会员中心嵌套路由
 * ============================================
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useMemberStore } from '@/stores/member'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', guestOnly: true },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
      meta: { title: '商品搜索' },
    },
    {
      path: '/category',
      name: 'category',
      component: () => import('@/views/CategoryView.vue'),
      meta: { title: '全部商品' },
    },
    {
      path: '/product/:id',
      name: 'product-detail',
      component: () => import('@/views/ProductDetailView.vue'),
      meta: { title: '商品详情' },
    },
    {
      path: '/brand',
      name: 'brand',
      component: () => import('@/views/BrandView.vue'),
      meta: { title: '品牌专区' },
    },
    {
      path: '/brand/:id',
      name: 'brand-detail',
      component: () => import('@/views/BrandDetailView.vue'),
      meta: { title: '品牌详情' },
    },
    {
      path: '/new',
      name: 'new',
      component: () => import('@/views/NewProductView.vue'),
      meta: { title: '新品上架' },
    },
    {
      path: '/hot',
      name: 'hot',
      component: () => import('@/views/HotProductView.vue'),
      meta: { title: '人气推荐' },
    },
    {
      path: '/coupons',
      name: 'coupon-center',
      component: () => import('@/views/CouponCenterView.vue'),
      meta: { title: '领券中心' },
    },
    {
      path: '/notice',
      name: 'notice-list',
      component: () => import('@/views/NoticeListView.vue'),
      meta: { title: '商城公告' },
    },
    {
      path: '/notice/:id',
      name: 'notice-detail',
      component: () => import('@/views/NoticeDetailView.vue'),
      meta: { title: '公告详情' },
    },
    {
      path: '/cart',
      name: 'cart',
      component: () => import('@/views/CartView.vue'),
      meta: { title: '购物车' },
    },
    {
      path: '/order-confirm',
      name: 'order-confirm',
      component: () => import('@/views/OrderConfirmView.vue'),
      meta: { title: '确认订单' },
    },
    {
      path: '/order/:id',
      name: 'order-detail',
      component: () => import('@/views/OrderDetailView.vue'),
      meta: { title: '订单详情' },
    },
    {
      path: '/pay',
      name: 'pay',
      component: () => import('@/views/PayView.vue'),
      meta: { title: '收银台' },
    },
    {
      path: '/pay/success',
      name: 'pay-success',
      component: () => import('@/views/PaySuccessView.vue'),
      meta: { title: '支付结果' },
    },
    {
      path: '/help',
      name: 'help',
      component: () => import('@/views/HelpView.vue'),
      meta: { title: '帮助中心' },
    },
    // ===== 会员中心嵌套路由 =====
    {
      path: '/member',
      component: () => import('@/views/member/MemberLayout.vue'),
      meta: { title: '会员中心' },
      children: [
        {
          path: '',
          name: 'member-home',
          component: () => import('@/views/member/MemberHomeView.vue'),
          meta: { title: '个人中心' },
        },
        {
          path: 'orders',
          name: 'member-orders',
          component: () => import('@/views/member/MemberOrdersView.vue'),
          meta: { title: '我的订单' },
        },
        {
          path: 'favorites',
          name: 'member-favorites',
          component: () => import('@/views/member/MemberFavoritesView.vue'),
          meta: { title: '我的收藏' },
        },
        {
          path: 'address',
          name: 'member-address',
          component: () => import('@/views/member/MemberAddressView.vue'),
          meta: { title: '收货地址' },
        },
        {
          path: 'coupons',
          name: 'member-coupons',
          component: () => import('@/views/member/MemberCouponsView.vue'),
          meta: { title: '我的优惠券' },
        },
        {
          path: 'history',
          name: 'member-history',
          component: () => import('@/views/member/MemberHistoryView.vue'),
          meta: { title: '浏览足迹' },
        },
        {
          path: 'brands',
          name: 'member-brands',
          component: () => import('@/views/member/MemberBrandFollowView.vue'),
          meta: { title: '品牌关注' },
        },
        {
          path: 'settings',
          name: 'member-settings',
          component: () => import('@/views/member/MemberSettingsView.vue'),
          meta: { title: '账号设置' },
        },
      ],
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const memberStore = useMemberStore()

  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - Mall PC Web`
  }

  // 需要登录的页面
  if (to.meta.requireAuth && !memberStore.isLoggedIn) {
    next(`/login?redirect=${to.path}`)
    return
  }

  // 仅限游客访问的页面（登录页、注册页）
  if (to.meta.guestOnly && memberStore.isLoggedIn) {
    next('/')
    return
  }

  next()
})

export default router
