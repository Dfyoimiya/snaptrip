import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, Select, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getNoticeListAPI, createNoticeAPI, updateNoticeAPI, deleteNoticeAPI, toggleNoticeStatusAPI } from '@/services/notice';

export default function NoticePage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Notice | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Notice>[] = [
    { title: '标题', dataIndex: 'title' },
    { title: '目标', dataIndex: 'targetType', width: 100, valueEnum: { ALL: '全部', CUSTOMER: 'C端', MERCHANT: '商家' } },
    { title: '状态', dataIndex: 'status', width: 80, render: (_, r) => <Tag color={r.status ? 'green' : 'default'}>{r.status ? '已发布' : '草稿'}</Tag> },
    { title: '发布时间', dataIndex: 'publishTime', search: false, valueType: 'dateTime' },
    { title: '创建时间', dataIndex: 'createdAt', search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option', width: 250,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <a key="status" onClick={async () => {
          const newStatus = record.status === 1 ? 0 : 1;
          await toggleNoticeStatusAPI(record.id, newStatus);
          message.success(newStatus ? '已发布' : '已撤回');
          actionRef.current?.reload();
        }}>{record.status ? '撤回' : '发布'}</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteNoticeAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateNoticeAPI(editing.id, values);
    } else {
      await createNoticeAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Notice>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getNoticeListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建公告
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑公告' : '新建公告'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="content" label="内容"><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="targetType" label="目标类型" initialValue="ALL">
            <Select options={[{ value: 'ALL', label: '全部' }, { value: 'CUSTOMER', label: 'C端用户' }, { value: 'MERCHANT', label: '商家' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
