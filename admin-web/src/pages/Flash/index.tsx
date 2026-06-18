import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, DatePicker, InputNumber, Select, message, Popconfirm, Space, Tabs } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import {
  getFlashPromotionListAPI, createFlashPromotionAPI, updateFlashPromotionAPI, deleteFlashPromotionAPI,
  getFlashSessionListAPI, createFlashSessionAPI, deleteFlashSessionAPI, toggleFlashSessionStatusAPI,
  getFlashProductListAPI, createFlashProductAPI, deleteFlashProductAPI,
} from '@/services/flash';
import dayjs from 'dayjs';

export default function FlashPage() {
  const [promotions, setPromotions] = useState<API.FlashPromotion[]>([]);
  const [sessions, setSessions] = useState<API.FlashSession[]>([]);
  const [products, setProducts] = useState<API.FlashProduct[]>([]);
  const [selectedPromo, setSelectedPromo] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [promoModalOpen, setPromoModalOpen] = useState(false);
  const [sessionModalOpen, setSessionModalOpen] = useState(false);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [editingPromo, setEditingPromo] = useState<API.FlashPromotion | null>(null);
  const [promoForm] = Form.useForm();
  const [sessionForm] = Form.useForm();
  const [productForm] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const fetchPromos = async () => {
    setLoading(true);
    try {
      const res = await getFlashPromotionListAPI({ page: 1, page_size: 100 });
      setPromotions(res.data.items);
    } finally { setLoading(false); }
  };

  const fetchSessions = async (promoId: string) => {
    const res = await getFlashSessionListAPI(promoId);
    setSessions(res.data);
  };

  const fetchProducts = async (promoId: string, sessionId: string) => {
    const res = await getFlashProductListAPI(promoId, sessionId, { page: 1, page_size: 100 });
    setProducts(res.data.items);
  };

  useEffect(() => { fetchPromos(); }, []);

  const promoTab = (
    <>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => { setEditingPromo(null); promoForm.resetFields(); setPromoModalOpen(true); }}>
        新建活动
      </Button>
      <Table<API.FlashPromotion>
        dataSource={promotions} rowKey="id" loading={loading}
        columns={[
          { title: '标题', dataIndex: 'title' },
          { title: '开始', dataIndex: 'startDate', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
          { title: '结束', dataIndex: 'endDate', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
          { title: '状态', dataIndex: 'status', render: (v: number) => ['未开始', '进行中', '已结束'][v] || v },
          {
            title: '操作', render: (_, r) => (
              <Space>
                <a onClick={() => { setEditingPromo(r); promoForm.setFieldsValue({ ...r, startDate: dayjs(r.startDate), endDate: dayjs(r.endDate) }); setPromoModalOpen(true); }}>编辑</a>
                <a onClick={() => { setSelectedPromo(r.id); fetchSessions(r.id); }}>场次</a>
                <Popconfirm title="确认删除?" onConfirm={async () => { await deleteFlashPromotionAPI(r.id); fetchPromos(); }}>
                  <a style={{ color: 'red' }}>删除</a>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </>
  );

  const sessionTab = selectedPromo ? (
    <>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => { sessionForm.resetFields(); setSessionModalOpen(true); }}>
        新建场次
      </Button>
      <Table<API.FlashSession>
        dataSource={sessions} rowKey="id"
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '开始', dataIndex: 'startTime', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
          { title: '结束', dataIndex: 'endTime', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
          { title: '状态', dataIndex: 'status', render: (v: number) => ['未开始', '进行中', '已结束'][v] || v },
          {
            title: '操作', render: (_, r) => (
              <Space>
                <a onClick={async () => {
                  const newStatus = r.status === 2 ? 1 : 2;
                  await toggleFlashSessionStatusAPI(selectedPromo, r.id, newStatus);
                  fetchSessions(selectedPromo);
                }}>{r.status === 2 ? '启用' : '停用'}</a>
                <a onClick={() => { setSelectedSession(r.id); fetchProducts(selectedPromo, r.id); }}>商品</a>
                <Popconfirm title="确认删除?" onConfirm={async () => { await deleteFlashSessionAPI(selectedPromo, r.id); fetchSessions(selectedPromo); }}>
                  <a style={{ color: 'red' }}>删除</a>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </>
  ) : <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>请先在"活动"tab中选择一个活动</div>;

  return (
    <div style={{ padding: 24 }}>
      <Tabs items={[
        { key: 'promo', label: '活动列表', children: promoTab },
        { key: 'session', label: '场次列表', children: sessionTab },
        { key: 'product', label: '秒杀商品', children: selectedSession ? (
          <Table<API.FlashProduct>
            dataSource={products} rowKey="id"
            columns={[
              { title: '商品ID', dataIndex: 'productId' },
              { title: 'SKU', dataIndex: 'skuId' },
              { title: '秒杀价', dataIndex: 'flashPrice', render: (v: number) => `¥${v}` },
              { title: '库存', dataIndex: 'flashStock' },
              { title: '限购', dataIndex: 'flashLimit' },
              {
                title: '操作', render: (_, r) => (
                  <Popconfirm title="确认删除?" onConfirm={async () => { await deleteFlashProductAPI(selectedPromo!, selectedSession, r.id); fetchProducts(selectedPromo!, selectedSession); }}>
                    <a style={{ color: 'red' }}>删除</a>
                  </Popconfirm>
                ),
              },
            ]}
          />
        ) : <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>请先在"场次"tab中选择一个场次</div> },
      ]} />

      {/* Promo Form Modal */}
      <Modal title={editingPromo ? '编辑活动' : '新建活动'} open={promoModalOpen} onOk={async () => {
        const values = promoForm.getFieldsValue();
        if (values.startDate) values.startDate = (values.startDate as dayjs.Dayjs).toISOString();
        if (values.endDate) values.endDate = (values.endDate as dayjs.Dayjs).toISOString();
        if (editingPromo) {
          await updateFlashPromotionAPI(editingPromo.id, values);
        } else {
          await createFlashPromotionAPI(values);
        }
        message.success('保存成功');
        setPromoModalOpen(false); fetchPromos();
      }} onCancel={() => setPromoModalOpen(false)}>
        <Form form={promoForm} layout="vertical">
          <Form.Item name="title" label="活动标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="startDate" label="开始日期" rules={[{ required: true }]}><DatePicker showTime /></Form.Item>
          <Form.Item name="endDate" label="结束日期" rules={[{ required: true }]}><DatePicker showTime /></Form.Item>
          <Form.Item name="note" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      {/* Session Form Modal */}
      <Modal title="新建场次" open={sessionModalOpen} onOk={async () => {
        const values = sessionForm.getFieldsValue();
        if (values.startTime) values.startTime = (values.startTime as dayjs.Dayjs).toISOString();
        if (values.endTime) values.endTime = (values.endTime as dayjs.Dayjs).toISOString();
        await createFlashSessionAPI(selectedPromo!, { name: values.name, startTime: values.startTime, endTime: values.endTime });
        message.success('创建成功');
        setSessionModalOpen(false); fetchSessions(selectedPromo!);
      }} onCancel={() => setSessionModalOpen(false)}>
        <Form form={sessionForm} layout="vertical">
          <Form.Item name="name" label="场次名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="startTime" label="开始时间" rules={[{ required: true }]}><DatePicker showTime /></Form.Item>
          <Form.Item name="endTime" label="结束时间" rules={[{ required: true }]}><DatePicker showTime /></Form.Item>
        </Form>
      </Modal>

      {/* Product Form Modal */}
      <Modal title="添加秒杀商品" open={productModalOpen} onOk={async () => {
        const values = productForm.getFieldsValue();
        await createFlashProductAPI(selectedPromo!, selectedSession!, values);
        message.success('添加成功');
        setProductModalOpen(false); fetchProducts(selectedPromo!, selectedSession!);
      }} onCancel={() => setProductModalOpen(false)}>
        <Form form={productForm} layout="vertical">
          <Form.Item name="productId" label="商品ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="skuId" label="SKU ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="flashPrice" label="秒杀价格" rules={[{ required: true }]}><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="flashStock" label="秒杀库存" rules={[{ required: true }]}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="flashLimit" label="限购数"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
