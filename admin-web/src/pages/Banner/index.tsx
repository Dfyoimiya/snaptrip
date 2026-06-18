import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, InputNumber, Select } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getBannerListAPI, createBannerAPI, updateBannerAPI, deleteBannerAPI, toggleBannerStatusAPI } from '@/services/cms';

export default function BannerPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Banner | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Banner>[] = [
    { title: '标题', dataIndex: 'title' },
    { title: '图片', dataIndex: 'pic', search: false, ellipsis: true },
    { title: '位置', dataIndex: 'position', width: 100, valueEnum: { HOME_TOP: '顶部', HOME_MIDDLE: '中部' } },
    { title: '排序', dataIndex: 'sort', width: 80, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: '禁用', 1: { text: '启用', status: 'Success' } } },
    {
      title: '操作', valueType: 'option', width: 250,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <a key="status" onClick={async () => {
          const newStatus = record.status === 1 ? 0 : 1;
          await toggleBannerStatusAPI(record.id, newStatus);
          message.success(newStatus ? '已启用' : '已禁用');
          actionRef.current?.reload();
        }}>{record.status ? '禁用' : '启用'}</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteBannerAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateBannerAPI(editing.id, values);
    } else {
      await createBannerAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Banner>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getBannerListAPI(params as Record<string, unknown>);
          return { data: res.data, total: (res.data as unknown as API.Banner[]).length, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={false}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建Banner
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑Banner' : '新建Banner'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="pic" label="图片URL" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="url" label="链接URL"><Input /></Form.Item>
          <Form.Item name="position" label="位置" initialValue="HOME_TOP">
            <Select options={[{ value: 'HOME_TOP', label: '首页顶部' }, { value: 'HOME_MIDDLE', label: '首页中部' }]} />
          </Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 0, label: '禁用' }, { value: 1, label: '启用' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
