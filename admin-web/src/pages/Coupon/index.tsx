import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, InputNumber, Select, DatePicker, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getCouponListAPI, createCouponAPI, updateCouponAPI, deleteCouponAPI } from '@/services/coupon';
import dayjs from 'dayjs';

const TYPE_OPTIONS = [
  { value: 0, label: '全场' }, { value: 1, label: '品类' }, { value: 2, label: '品牌' },
];
const USE_TYPE_OPTIONS = [
  { value: 0, label: '满减' }, { value: 1, label: '折扣' }, { value: 2, label: '立减' },
];

export default function CouponPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Coupon | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Coupon>[] = [
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'type', width: 80, valueEnum: { 0: '全场', 1: '品类', 2: '品牌' } },
    { title: '使用类型', dataIndex: 'useType', width: 80, search: false, valueEnum: { 0: '满减', 1: '折扣', 2: '立减' } },
    { title: '面额', dataIndex: 'amount', width: 100, search: false, render: (v: number) => `¥${v}` },
    { title: '门槛', dataIndex: 'minAmount', width: 100, search: false, render: (v: number) => `¥${v}` },
    { title: '发放/领取/使用', width: 150, search: false,
      render: (_, r) => `${r.publishCount}/${r.receiveCount}/${r.useCount}` },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: '停用', 1: { text: '启用', status: 'Success' } } },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue({ ...record, startTime: record.startTime ? dayjs(record.startTime) : null, endTime: record.endTime ? dayjs(record.endTime) : null }); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteCouponAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (values.startTime) values.startTime = (values.startTime as dayjs.Dayjs).toISOString();
    if (values.endTime) values.endTime = (values.endTime as dayjs.Dayjs).toISOString();
    if (editing?.id) {
      await updateCouponAPI(editing.id, values);
    } else {
      await createCouponAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Coupon>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getCouponListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新建优惠券</Button>,
        ]}
      />
      <Modal title={editing ? '编辑优惠券' : '新建优惠券'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="类型" initialValue={0}>
            <Select options={TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item name="useType" label="优惠方式" initialValue={0}>
            <Select options={USE_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item name="amount" label="面额" rules={[{ required: true }]}><InputNumber min={0} precision={2} style={{ width: 200 }} /></Form.Item>
          <Form.Item name="minAmount" label="使用门槛"><InputNumber min={0} precision={2} style={{ width: 200 }} /></Form.Item>
          <Form.Item name="count" label="发放总量" rules={[{ required: true }]}><InputNumber min={1} style={{ width: 200 }} /></Form.Item>
          <Form.Item name="perLimit" label="每人限领 (0=不限)"><InputNumber min={0} style={{ width: 200 }} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 0, label: '停用' }, { value: 1, label: '启用' }]} />
          </Form.Item>
          <Form.Item name="startTime" label="开始时间"><DatePicker showTime /></Form.Item>
          <Form.Item name="endTime" label="结束时间"><DatePicker showTime /></Form.Item>
          <Form.Item name="note" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
