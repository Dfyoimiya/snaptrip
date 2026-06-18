import { ProTable, ModalForm, ProFormText } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, message, Popconfirm, Space } from 'antd';
import { useRef } from 'react';
import { useNavigate } from '@umijs/max';
import {
  getOrderListAPI, closeOrderAPI, deliveryOrderAPI, remarkOrderAPI, deleteOrderAPI, refundOrderAPI,
} from '@/services/order';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待付款', color: 'orange' },
  1: { text: '已付款', color: 'blue' },
  2: { text: '已发货', color: 'cyan' },
  3: { text: '已收货', color: 'green' },
  4: { text: '已完成', color: 'green' },
  5: { text: '已关闭', color: 'default' },
  6: { text: '退款中', color: 'red' },
  7: { text: '已退款', color: 'default' },
};

export default function OrderList() {
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();

  const columns: ProColumns<API.Order>[] = [
    { title: '订单编号', dataIndex: 'orderSn', width: 180 },
    { title: '用户', dataIndex: 'memberUsername', width: 120 },
    { title: '实付金额', dataIndex: 'payAmount', width: 100, search: false, render: (_, r) => `¥${r.payAmount}` },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (_, r) => <Tag color={STATUS_MAP[r.status]?.color}>{STATUS_MAP[r.status]?.text || r.status}</Tag>,
      valueEnum: {
        0: '待付款', 1: '已付款', 2: '已发货', 3: '已收货', 4: '已完成', 5: '已关闭', 6: '退款中', 7: '已退款',
      },
    },
    { title: '收货人', dataIndex: 'receiverName', width: 100, search: false },
    { title: '创建时间', dataIndex: 'createdAt', width: 160, search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option', width: 300,
      render: (_, record) => {
        const actions: React.ReactNode[] = [
          <a key="detail" onClick={() => navigate(`/order/${record.id}`)}>详情</a>,
        ];
        if (record.status === 1) {
          actions.push(
            <ModalForm
              key="delivery"
              title="发货"
              trigger={<a>发货</a>}
              onFinish={async (values) => {
                await deliveryOrderAPI(record.id, values as API.OrderDelivery);
                message.success('发货成功');
                actionRef.current?.reload();
                return true;
              }}
            >
              <ProFormText name="deliveryCompany" label="物流公司" rules={[{ required: true }]} />
              <ProFormText name="deliverySn" label="物流单号" rules={[{ required: true }]} />
            </ModalForm>,
          );
        }
        if ([0, 1].includes(record.status)) {
          actions.push(
            <Popconfirm key="close" title="确认关闭?" onConfirm={async () => {
              await closeOrderAPI(record.id); message.success('已关闭'); actionRef.current?.reload();
            }}><a>关闭</a></Popconfirm>,
          );
        }
        if (record.status === 6) {
          actions.push(
            <Popconfirm key="refund" title="确认退款?" onConfirm={async () => {
              await refundOrderAPI(record.id); message.success('已退款'); actionRef.current?.reload();
            }}><a>退款</a></Popconfirm>,
          );
        }
        actions.push(
          <ModalForm
            key="remark"
            title="备注"
            trigger={<a>备注</a>}
            onFinish={async (values) => {
              await remarkOrderAPI(record.id, values.note);
              message.success('备注成功');
              actionRef.current?.reload();
              return true;
            }}
          >
            <ProFormText name="note" label="备注内容" rules={[{ required: true }]} />
          </ModalForm>,
          <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
            await deleteOrderAPI(record.id); message.success('已删除'); actionRef.current?.reload();
          }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
        );
        return actions;
      },
    },
  ];

  return (
    <ProTable<API.Order>
      columns={columns}
      actionRef={actionRef}
      request={async (params) => {
        const res = await getOrderListAPI(params as Record<string, unknown>);
        return { data: res.data.items, total: res.data.total, success: true };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      pagination={{ pageSize: 20 }}
    />
  );
}
