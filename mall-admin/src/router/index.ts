import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordExt } from '@/types'
import Layout from '@/views/layout/Layout.vue'

// ========== 常量路由（无需权限） ==========
export const constantRouterMap: RouteRecordExt[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/index.vue'),
    hidden: true,
    meta: { title: '登录', hidden: true },
  },
  {
    path: '/404',
    name: '404',
    component: () => import('@/views/normal/404/index.vue'),
    hidden: true,
    meta: { title: '404', hidden: true },
  },
  // 根路由 - Layout 布局
  {
    path: '/',
    component: Layout,
    redirect: '/home',
    meta: { title: '首页', icon: 'HomeFilled' },
    children: [
      {
        path: 'home',
        name: 'home',
        component: () => import('@/views/home/index.vue'),
        meta: { title: '首页', icon: 'HomeFilled', keepAlive: true },
      },
    ],
  },
]

// ========== 动态路由（需要权限） ==========
export const asyncRouterMap: RouteRecordExt[] = [
  // 商品管理 (pms)
  {
    path: '/pms',
    component: Layout,
    redirect: '/pms/product',
    name: 'pms',
    meta: { title: '商品管理', icon: 'Goods' },
    children: [
      {
        path: 'product',
        name: 'product',
        component: () => import('@/views/pms/product/index.vue'),
        meta: { title: '商品列表', icon: 'List', keepAlive: true },
      },
      {
        path: 'addProduct',
        name: 'addProduct',
        component: () => import('@/views/pms/product/add.vue'),
        meta: { title: '添加商品', icon: 'Plus' },
        hidden: true,
      },
      {
        path: 'updateProduct',
        name: 'updateProduct',
        component: () => import('@/views/pms/product/update.vue'),
        meta: { title: '编辑商品', icon: 'Edit' },
        hidden: true,
      },
      {
        path: 'productCate',
        name: 'productCate',
        component: () => import('@/views/pms/productCate/index.vue'),
        meta: { title: '商品分类', icon: 'FolderOpened', keepAlive: true },
      },
      {
        path: 'productAttr',
        name: 'productAttr',
        component: () => import('@/views/pms/productAttr/index.vue'),
        meta: { title: '商品类型', icon: 'Collection', keepAlive: true },
      },
      {
        path: 'brand',
        name: 'brand',
        component: () => import('@/views/pms/brand/index.vue'),
        meta: { title: '品牌管理', icon: 'Trophy', keepAlive: true },
      },
    ],
  },
  // 订单管理 (oms)
  {
    path: '/oms',
    component: Layout,
    redirect: '/oms/order',
    name: 'oms',
    meta: { title: '订单管理', icon: 'Document' },
    children: [
      {
        path: 'order',
        name: 'order',
        component: () => import('@/views/oms/order/index.vue'),
        meta: { title: '订单列表', icon: 'List', keepAlive: true },
      },
      {
        path: 'orderDetail',
        name: 'orderDetail',
        component: () => import('@/views/oms/order/detail.vue'),
        meta: { title: '订单详情', icon: 'Document' },
        hidden: true,
      },
      {
        path: 'orderSetting',
        name: 'orderSetting',
        component: () => import('@/views/oms/order/setting.vue'),
        meta: { title: '订单设置', icon: 'Setting' },
      },
      {
        path: 'returnApply',
        name: 'returnApply',
        component: () => import('@/views/oms/apply/index.vue'),
        meta: { title: '退货申请', icon: 'RefreshLeft', keepAlive: true },
      },
      {
        path: 'returnApplyDetail',
        name: 'returnApplyDetail',
        component: () => import('@/views/oms/apply/applyDetail.vue'),
        meta: { title: '退货详情', icon: 'Document' },
        hidden: true,
      },
      {
        path: 'returnReason',
        name: 'returnReason',
        component: () => import('@/views/oms/apply/reason.vue'),
        meta: { title: '退货原因', icon: 'Warning', keepAlive: true },
      },
    ],
  },
  // 会员管理 (ums)
  {
    path: '/ums',
    component: Layout,
    redirect: '/ums/member',
    name: 'ums',
    meta: { title: '会员管理', icon: 'User' },
    children: [
      {
        path: 'member',
        name: 'member',
        component: () => import('@/views/ums/member/index.vue'),
        meta: { title: '会员列表', icon: 'List', keepAlive: true },
      },
      {
        path: 'admin',
        name: 'admin',
        component: () => import('@/views/ums/admin/index.vue'),
        meta: { title: '用户管理', icon: 'UserFilled', keepAlive: true },
      },
      {
        path: 'role',
        name: 'role',
        component: () => import('@/views/ums/role/index.vue'),
        meta: { title: '角色管理', icon: 'Medal', keepAlive: true },
      },
      {
        path: 'allocMenu',
        name: 'allocMenu',
        component: () => import('@/views/ums/role/allocMenu.vue'),
        meta: { title: '分配菜单', icon: 'Menu' },
        hidden: true,
      },
      {
        path: 'allocResource',
        name: 'allocResource',
        component: () => import('@/views/ums/role/allocResource.vue'),
        meta: { title: '分配资源', icon: 'Collection' },
        hidden: true,
      },
      {
        path: 'menu',
        name: 'menu',
        component: () => import('@/views/ums/menu/index.vue'),
        meta: { title: '菜单管理', icon: 'Menu', keepAlive: true },
      },
      {
        path: 'resource',
        name: 'resource',
        component: () => import('@/views/ums/resource/index.vue'),
        meta: { title: '资源管理', icon: 'Collection', keepAlive: true },
      },
    ],
  },
  // 营销管理 (sms)
  {
    path: '/sms',
    component: Layout,
    redirect: '/sms/coupon',
    name: 'sms',
    meta: { title: '营销管理', icon: 'Promotion' },
    children: [
      {
        path: 'coupon',
        name: 'coupon',
        component: () => import('@/views/sms/coupon/index.vue'),
        meta: { title: '优惠券', icon: 'Ticket', keepAlive: true },
      },
      {
        path: 'addCoupon',
        name: 'addCoupon',
        component: () => import('@/views/sms/coupon/add.vue'),
        meta: { title: '添加优惠券', icon: 'Plus' },
        hidden: true,
      },
      {
        path: 'updateCoupon',
        name: 'updateCoupon',
        component: () => import('@/views/sms/coupon/update.vue'),
        meta: { title: '编辑优惠券', icon: 'Edit' },
        hidden: true,
      },
      {
        path: 'couponDetail',
        name: 'couponDetail',
        component: () => import('@/views/sms/coupon/update.vue'),
        meta: { title: '优惠券详情', icon: 'Document' },
        hidden: true,
      },
      {
        path: 'flash',
        name: 'flash',
        component: () => import('@/views/sms/flash/index.vue'),
        meta: { title: '秒杀活动', icon: 'Timer', keepAlive: true },
      },
      {
        path: 'brandRecommend',
        name: 'brandRecommend',
        component: () => import('@/views/sms/brandRecommend/index.vue'),
        meta: { title: '品牌推荐', icon: 'Trophy', keepAlive: true },
      },
    ],
  },
  // 内容管理 (cms)
  {
    path: '/cms',
    component: Layout,
    redirect: '/cms/banner',
    name: 'cms',
    meta: { title: '内容管理', icon: 'DocumentCopy' },
    children: [
      {
        path: 'banner',
        name: 'banner',
        component: () => import('@/views/cms/banner/index.vue'),
        meta: { title: '轮播广告', icon: 'Picture', keepAlive: true },
      },
      {
        path: 'subject',
        name: 'subject',
        component: () => import('@/views/cms/subject/index.vue'),
        meta: { title: '专题管理', icon: 'Notebook', keepAlive: true },
      },
    ],
  },
  // 系统设置
  {
    path: '/setting',
    component: Layout,
    redirect: '/setting/oss',
    name: 'setting',
    meta: { title: '系统设置', icon: 'Tools' },
    children: [
      {
        path: 'oss',
        name: 'oss',
        component: () => import('@/views/setting/oss/index.vue'),
        meta: { title: '文件存储', icon: 'UploadFilled', keepAlive: true },
      },
    ],
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: constantRouterMap as any,
})

export default router
