import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, message, Popconfirm, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getReturnReasonListAPI, createReturnReasonAPI, updateReturnReasonAPI, deleteReturnReasonAPI } from '@/services/return';

export default function ReturnReasonPage() {
  const [data, setData] = useState<API.ReturnReason[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.ReturnReason | null>(null);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try { const res = await getReturnReasonListAPI(); setData(res.data); } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const columns = [
    { title: '原因', dataIndex: 'name' },
    { title: '排序', dataIndex: 'sort' },
    { title: '状态', dataIndex: 'status', render: (v: number) => v ? '启用' : '禁用' },
    {
      title: '操作', render: (_: unknown, r: API.ReturnReason) => (
        <Space>
          <a onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</a>
          <Popconfirm title="确认删除?" onConfirm={async () => { await deleteReturnReasonAPI(r.id); message.success('已删除'); fetchData(); }}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateReturnReasonAPI(editing.id, values);
    } else {
      await createReturnReasonAPI(values);
    }
    message.success('保存成功');
    setModalOpen(false); setEditing(null); fetchData();
  };

  return (
    <div style={{ padding: 24 }}>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }}
        onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
        新建退货原因
      </Button>
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={false} />
      <Modal title={editing ? '编辑退货原因' : '新建退货原因'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="原因" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
