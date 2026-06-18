import type { ProLayoutProps } from '@ant-design/pro-components';
import {
  DashboardOutlined,
  ShoppingOutlined,
  TagOutlined,
  AppstoreOutlined,
  ProfileOutlined,
  OrderedListOutlined,
  FileProtectOutlined,
  UserOutlined,
  GiftOutlined,
  ThunderboltOutlined,
  PictureOutlined,
  ReadOutlined,
  QuestionCircleOutlined,
  NotificationOutlined,
  CustomerServiceOutlined,
  SettingOutlined,
  TeamOutlined,
  SafetyCertificateOutlined,
  MenuOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from '@umijs/max';
import { useState } from 'react';
import { Dropdown } from 'antd';

export default function BasicLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const route: ProLayoutProps['route'] = {
    routes: [
      { path: '/dashboard', name: '仪表盘', icon: <DashboardOutlined /> },
      {
        path: '/product',
        name: '商品管理',
        icon: <ShoppingOutlined />,
        routes: [
          { path: '/product/list', name: '商品列表' },
          { path: '/product/create', name: '新建商品' },
          { path: '/brand', name: '品牌管理' },
          { path: '/category', name: '分类管理' },
          { path: '/attribute', name: '属性管理' },
        ],
      },
      {
        path: '/order',
        name: '订单管理',
        icon: <OrderedListOutlined />,
        routes: [
          { path: '/order/list', name: '订单列表' },
          { path: '/return/list', name: '退货申请' },
          { path: '/return/reason', name: '退货原因' },
        ],
      },
      { path: '/member', name: '会员管理', icon: <UserOutlined /> },
      {
        path: '/marketing',
        name: '营销管理',
        icon: <GiftOutlined />,
        routes: [
          { path: '/coupon', name: '优惠券' },
          { path: '/flash', name: '秒杀活动' },
        ],
      },
      {
        path: '/content',
        name: '内容管理',
        icon: <PictureOutlined />,
        routes: [
          { path: '/banner', name: '轮播图' },
          { path: '/subject', name: '专题管理' },
          { path: '/help', name: '帮助中心' },
          { path: '/notice', name: '公告管理' },
        ],
      },
      {
        path: '/cs',
        name: '客服管理',
        icon: <CustomerServiceOutlined />,
        routes: [{ path: '/cs/tickets', name: '工单管理' }],
      },
      {
        path: '/system',
        name: '系统管理',
        icon: <SettingOutlined />,
        routes: [
          { path: '/system/admin', name: '管理员' },
          { path: '/system/role', name: '角色' },
          { path: '/system/menu', name: '菜单' },
          { path: '/system/resource', name: '资源' },
        ],
      },
    ],
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <div style={{ height: '100vh' }}>
      <ProLayout
        title="SnapTrip"
        logo={null}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        location={{ pathname: location.pathname }}
        route={route}
        menuItemRender={(item, dom) => (
          <a onClick={() => navigate(item.path || '/')}>{dom}</a>
        )}
        rightContentRender={() => (
          <Dropdown
            menu={{
              items: [{ key: 'logout', label: '退出登录', onClick: handleLogout }],
            }}
          >
            <a style={{ color: '#fff' }}>管理员</a>
          </Dropdown>
        )}
      >
        <Outlet />
      </ProLayout>
    </div>
  );
}
