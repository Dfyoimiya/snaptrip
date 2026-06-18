import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, message, Popconfirm, Modal, Form, InputNumber, Select, Input } from 'antd';
import { useRef, useState } from 'react';
import { useNavigate } from '@umijs/max';
import { getReturnApplyListAPI, updateReturnApplyStatusAPI, deleteReturnAppliesAPI } from '@/services/return';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待处理', color: 'orange' },
  1: { text: '已通过', color: 'blue' },
  2: { text: '已拒绝', color: 'red' },
  3: { text: '已退款', color: 'green' },
};

export default function ReturnList() {
  const actionRef = useRef<ActionType>();
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.ReturnApply>[] = [
    { title: 'ID', dataIndex: 'id', width: 100, search: false },
    { title: '订单编号', dataIndex: 'orderSn', width: 180 },
    { title: '用户', dataIndex: 'memberUsername', width: 120 },
    { title: '商品', dataIndex: 'productName', ellipsis: true },
    { title: '退货数量', dataIndex: 'productCount', width: 80, search: false },
    { title: '退款金额', dataIndex: 'returnAmount', width: 100, search: false, render: (v: number) => v ? `¥${v}` : '-' },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (_, r) => <Tag color={STATUS_MAP[r.status]?.color}>{STATUS_MAP[r.status]?.text || r.status}</Tag>,
      valueEnum: { 0: '待处理', 1: '已通过', 2: '已拒绝', 3: '已退款' },
    },
    { title: '处理人', dataIndex: 'handleMan', width: 100 },
    { title: '申请时间', dataIndex: 'createdAt', width: 160, search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        record.status === 0 && (
          <a key="handle" onClick={() => { setCurrentId(record.id); form.resetFields(); setStatusModalOpen(true); }}>处理</a>
        ),
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteReturnAppliesAPI([record.id]); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable<API.ReturnApply>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getReturnApplyListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{ pageSize: 20 }}
      />
      <Modal title="处理退货申请" open={statusModalOpen} onOk={async () => {
        const values = form.getFieldsValue();
        if (currentId) {
          await updateReturnApplyStatusAPI(currentId, values);
          message.success('已处理');
          setStatusModalOpen(false);
          actionRef.current?.reload();
        }
      }} onCancel={() => setStatusModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="status" label="处理结果" rules={[{ required: true }]}>
            <Select options={[
              { value: 1, label: '通过' }, { value: 2, label: '拒绝' }, { value: 3, label: '退款完成' },
            ]} />
          </Form.Item>
          <Form.Item name="handleNote" label="处理备注"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="returnAmount" label="退款金额"><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
