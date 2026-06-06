import type { LoginForm, UserInfo } from '@/types'

// 模拟登录 API（实际项目中替换为真实接口）
export function loginApi(data: LoginForm): Promise<{ code: number; data: UserInfo; message: string }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        code: 200,
        data: {
          username: data.username,
          nickname: '管理员',
          avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
          token: `mock_token_${Date.now()}`,
          menus: [
            { id: 1, parentId: 0, title: '商品管理', name: 'pms', icon: 'Goods', sort: 5, hidden: 0 },
            { id: 2, parentId: 1, title: '商品列表', name: 'product', icon: 'List', sort: 4, hidden: 0 },
            { id: 3, parentId: 1, title: '添加商品', name: 'addProduct', icon: 'Plus', sort: 3, hidden: 0 },
            { id: 4, parentId: 1, title: '商品分类', name: 'productCate', icon: 'FolderOpened', sort: 2, hidden: 0 },
            { id: 5, parentId: 1, title: '商品类型', name: 'productAttr', icon: 'Collection', sort: 1, hidden: 0 },
            { id: 13, parentId: 1, title: '品牌管理', name: 'brand', icon: 'Trophy', sort: 0, hidden: 0 },
            { id: 6, parentId: 0, title: '订单管理', name: 'oms', icon: 'Document', sort: 4, hidden: 0 },
            { id: 7, parentId: 6, title: '订单列表', name: 'order', icon: 'List', sort: 3, hidden: 0 },
            { id: 8, parentId: 6, title: '订单设置', name: 'orderSetting', icon: 'Setting', sort: 2, hidden: 0 },
            { id: 9, parentId: 6, title: '退货申请', name: 'returnApply', icon: 'RefreshLeft', sort: 1, hidden: 0 },
            { id: 14, parentId: 6, title: '退货原因', name: 'returnReason', icon: 'Warning', sort: 0, hidden: 0 },
            { id: 10, parentId: 0, title: '会员管理', name: 'ums', icon: 'User', sort: 3, hidden: 0 },
            { id: 11, parentId: 10, title: '用户管理', name: 'admin', icon: 'UserFilled', sort: 4, hidden: 0 },
            { id: 12, parentId: 10, title: '角色管理', name: 'role', icon: 'Medal', sort: 3, hidden: 0 },
            { id: 15, parentId: 10, title: '菜单管理', name: 'menu', icon: 'Menu', sort: 2, hidden: 0 },
            { id: 16, parentId: 10, title: '资源管理', name: 'resource', icon: 'Collection', sort: 1, hidden: 0 },
            { id: 17, parentId: 10, title: '会员列表', name: 'member', icon: 'List', sort: 0, hidden: 0 },
            { id: 18, parentId: 0, title: '营销管理', name: 'sms', icon: 'Promotion', sort: 2, hidden: 0 },
            { id: 19, parentId: 18, title: '优惠券', name: 'coupon', icon: 'Ticket', sort: 2, hidden: 0 },
            { id: 20, parentId: 18, title: '秒杀活动', name: 'flash', icon: 'Timer', sort: 1, hidden: 0 },
            { id: 21, parentId: 18, title: '品牌推荐', name: 'brandRecommend', icon: 'Trophy', sort: 0, hidden: 0 },
            { id: 22, parentId: 0, title: '内容管理', name: 'cms', icon: 'DocumentCopy', sort: 1, hidden: 0 },
            { id: 23, parentId: 22, title: '轮播广告', name: 'banner', icon: 'Picture', sort: 1, hidden: 0 },
            { id: 24, parentId: 22, title: '专题管理', name: 'subject', icon: 'Notebook', sort: 0, hidden: 0 },
            { id: 25, parentId: 0, title: '系统设置', name: 'setting', icon: 'Tools', sort: 0, hidden: 0 },
            { id: 26, parentId: 25, title: '文件存储', name: 'oss', icon: 'UploadFilled', sort: 0, hidden: 0 },
          ],
          roles: ['admin'],
        },
        message: '登录成功',
      })
    }, 500)
  })
}

// 登出 API
export function logoutApi(): Promise<{ code: number; data: null; message: string }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ code: 200, data: null, message: '登出成功' })
    }, 300)
  })
}
