import { defineConfig } from '@umijs/max';

export default defineConfig({
  presets: ['@umijs/max/dist/preset'],

  title: 'SnapTrip Admin',

  // API proxy — forward /api to backend
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },

  // Ant Design theme
  antd: {
    theme: {
      token: {
        colorPrimary: '#1677ff',
        borderRadius: 6,
      },
    },
  },

  // Route config — generated from src/routes.ts
  routes: [
    {
      path: '/login',
      component: './Login',
      layout: false,
    },
    {
      path: '/',
      component: '@/layouts/BasicLayout',
      routes: [
        { path: '/', redirect: '/dashboard' },
        { path: '/dashboard', component: './Dashboard' },

        // Product Management
        { path: '/product/list', component: './Product/List' },
        { path: '/product/create', component: './Product/Form' },
        { path: '/product/:id', component: './Product/Form' },
        { path: '/brand', component: './Brand' },
        { path: '/category', component: './Category' },
        { path: '/attribute', component: './Attribute' },

        // Order Management
        { path: '/order/list', component: './Order/List' },
        { path: '/order/:id', component: './Order/Detail' },
        { path: '/return/list', component: './Return/List' },
        { path: '/return/reason', component: './Return/Reason' },

        // User Management
        { path: '/member', component: './Member' },

        // Marketing
        { path: '/coupon', component: './Coupon' },
        { path: '/flash', component: './Flash' },

        // Content
        { path: '/banner', component: './Banner' },
        { path: '/subject', component: './Subject' },
        { path: '/help', component: './Help' },
        { path: '/notice', component: './Notice' },

        // Customer Service
        { path: '/cs/tickets', component: './CustomerService/TicketList' },
        { path: '/cs/tickets/:id', component: './CustomerService/TicketDetail' },

        // System
        { path: '/system/admin', component: './System/Admin' },
        { path: '/system/role', component: './System/Role' },
        { path: '/system/menu', component: './System/Menu' },
        { path: '/system/resource', component: './System/Resource' },
      ],
    },
  ],

  // Enable hash routing for easy deployment
  history: { type: 'hash' },

  // Plugins
  model: {},
  access: {},
  initialState: {},
  request: {},

  // npm client
  npmClient: 'npm',
});
