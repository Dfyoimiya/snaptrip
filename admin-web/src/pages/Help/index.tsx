import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, InputNumber, Select } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getHelpListAPI, createHelpAPI, updateHelpAPI, deleteHelpAPI } from '@/services/cms';

export default function HelpPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Help | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Help>[] = [
    { title: '标题', dataIndex: 'title' },
    { title: '分类', dataIndex: 'categoryName', width: 120 },
    { title: '排序', dataIndex: 'sort', width: 80, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: '隐藏', 1: { text: '显示', status: 'Success' } } },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteHelpAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateHelpAPI(editing.id, values);
    } else {
      await createHelpAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Help>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getHelpListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建帮助
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑帮助' : '新建帮助'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="content" label="内容"><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="categoryName" label="分类"><Input /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 0, label: '隐藏' }, { value: 1, label: '显示' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
