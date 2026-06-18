import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, message, Space, Popconfirm } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef } from 'react';
import { useNavigate } from '@umijs/max';
import {
  getProductListAPI,
  deleteProductAPI,
  toggleProductStatusAPI,
  toggleProductNewAPI,
  toggleProductRecommendAPI,
} from '@/services/product';

export default function ProductList() {
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();

  const columns: ProColumns<API.Product>[] = [
    { title: 'ID', dataIndex: 'id', width: 100, search: false },
    { title: '商品名称', dataIndex: 'name', ellipsis: true },
    { title: '货号', dataIndex: 'productSn', width: 120 },
    { title: '品牌', dataIndex: 'brandName', width: 100, search: false },
    { title: '分类', dataIndex: 'categoryName', width: 100, search: false },
    {
      title: '价格', dataIndex: 'price', width: 100, search: false,
      render: (_, r) => `¥${r.price}`,
    },
    {
      title: '库存', dataIndex: 'stock', width: 80, search: false,
    },
    {
      title: '上架', dataIndex: 'publishStatus', width: 80,
      valueEnum: { 0: { text: '下架', status: 'Default' }, 1: { text: '上架', status: 'Success' } },
    },
    {
      title: '审核', dataIndex: 'verifyStatus', width: 80,
      valueEnum: { 0: { text: '待审', status: 'Warning' }, 1: { text: '通过', status: 'Success' }, 2: { text: '驳回', status: 'Error' } },
    },
    {
      title: '新品', dataIndex: 'newStatus', width: 80, search: false,
      valueEnum: { 0: { text: '否' }, 1: { text: '是', status: 'Processing' } },
    },
    {
      title: '推荐', dataIndex: 'recommendStatus', width: 80, search: false,
      valueEnum: { 0: { text: '否' }, 1: { text: '是', status: 'Success' } },
    },
    {
      title: '操作', valueType: 'option', width: 280,
      render: (_, record) => [
        <a key="edit" onClick={() => navigate(`/product/${record.id}`)}>编辑</a>,
        <a key="shelf" onClick={async () => {
          const newStatus = record.publishStatus === 1 ? 0 : 1;
          await toggleProductStatusAPI(record.id, newStatus);
          message.success(newStatus ? '已上架' : '已下架');
          actionRef.current?.reload();
        }}>{record.publishStatus === 1 ? '下架' : '上架'}</a>,
        <a key="new" onClick={async () => {
          await toggleProductNewAPI(record.id, record.newStatus === 1 ? 0 : 1);
          actionRef.current?.reload();
        }}>{record.newStatus ? '取消新品' : '设新品'}</a>,
        <a key="rec" onClick={async () => {
          await toggleProductRecommendAPI(record.id, record.recommendStatus === 1 ? 0 : 1);
          actionRef.current?.reload();
        }}>{record.recommendStatus ? '取消推荐' : '设推荐'}</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteProductAPI(record.id);
          message.success('已删除');
          actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  return (
    <ProTable<API.Product>
      columns={columns}
      actionRef={actionRef}
      request={async (params) => {
        const res = await getProductListAPI(params as Record<string, unknown>);
        return { data: res.data.items, total: res.data.total, success: true };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      pagination={{ pageSize: 20 }}
      toolBarRender={() => [
        <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => navigate('/product/create')}>
          新建商品
        </Button>,
      ]}
    />
  );
}
