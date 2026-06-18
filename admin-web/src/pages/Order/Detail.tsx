import { useEffect, useState } from 'react';
import { Card, Descriptions, Table, Tag, Spin, message, Popconfirm } from 'antd';
import { useParams } from '@umijs/max';
import { getOrderDetailAPI, closeOrderAPI, deliveryOrderAPI, refundOrderAPI } from '@/services/order';
import { ModalForm, ProFormText } from '@ant-design/pro-components';

const STATUS_MAP: Record<number, string> = {
  0: '待付款', 1: '已付款', 2: '已发货', 3: '已收货', 4: '已完成', 5: '已关闭', 6: '退款中', 7: '已退款',
};

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<API.Order | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await getOrderDetailAPI(id);
      setOrder(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDetail(); }, [id]);

  if (loading) return <Spin style={{ display: 'block', margin: '100px auto' }} />;
  if (!order) return null;

  const itemCols = [
    { title: '商品', dataIndex: 'productName' },
    { title: '规格', dataIndex: 'spec' },
    { title: 'SKU', dataIndex: 'skuCode' },
    { title: '单价', dataIndex: 'price', render: (v: number) => `¥${v}` },
    { title: '数量', dataIndex: 'quantity' },
  ];

  const logCols = [
    { title: '操作人', dataIndex: 'operateMan' },
    { title: '操作前状态', dataIndex: 'orderStatusBefore', render: (v: number) => v != null ? STATUS_MAP[v] : '-' },
    { title: '操作后状态', dataIndex: 'orderStatusAfter', render: (v: number) => STATUS_MAP[v] || v },
    { title: '备注', dataIndex: 'note' },
    { title: '时间', dataIndex: 'createdAt' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title={`订单 ${order.orderSn}`} extra={<Tag>{STATUS_MAP[order.status]}</Tag>}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="用户">{order.memberUsername}</Descriptions.Item>
          <Descriptions.Item label="总金额">¥{order.totalAmount}</Descriptions.Item>
          <Descriptions.Item label="实付">¥{order.payAmount}</Descriptions.Item>
          <Descriptions.Item label="运费">¥{order.freightAmount}</Descriptions.Item>
          <Descriptions.Item label="优惠">¥{order.discountAmount}</Descriptions.Item>
          <Descriptions.Item label="支付方式">{['', '微信', '支付宝'][order.payType] || '未支付'}</Descriptions.Item>
          <Descriptions.Item label="支付时间">{order.paymentTime || '-'}</Descriptions.Item>
          <Descriptions.Item label="物流公司">{order.deliveryCompany || '-'}</Descriptions.Item>
          <Descriptions.Item label="物流单号">{order.deliverySn || '-'}</Descriptions.Item>
          <Descriptions.Item label="收货人">{order.receiverName}</Descriptions.Item>
          <Descriptions.Item label="电话">{order.receiverPhone}</Descriptions.Item>
          <Descriptions.Item label="地址">
            {[order.receiverProvince, order.receiverCity, order.receiverRegion, order.receiverDetailAddress].filter(Boolean).join(' ')}
          </Descriptions.Item>
          <Descriptions.Item label="备注">{order.note || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="商品明细" style={{ marginTop: 16 }}>
        <Table columns={itemCols} dataSource={order.items} rowKey="id" size="small" pagination={false} />
      </Card>

      <Card title="操作日志" style={{ marginTop: 16 }}>
        <Table columns={logCols} dataSource={order.logs} rowKey="id" size="small" pagination={false} />
      </Card>
    </div>
  );
}
