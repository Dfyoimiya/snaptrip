import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getBrandListAPI, createBrandAPI, updateBrandAPI, deleteBrandAPI } from '@/services/brand';
import { Modal, Form, Input, InputNumber, Select } from 'antd';

export default function BrandPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Brand | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Brand>[] = [
    { title: 'ID', dataIndex: 'id', width: 100, search: false },
    { title: '品牌名称', dataIndex: 'name' },
    { title: '首字母', dataIndex: 'firstLetter', width: 80 },
    { title: '排序', dataIndex: 'sort', width: 80, search: false },
    {
      title: '显示', dataIndex: 'showStatus', width: 80,
      valueEnum: { 0: { text: '隐藏' }, 1: { text: '显示', status: 'Success' } },
    },
    { title: 'Logo', dataIndex: 'logo', width: 120, search: false, ellipsis: true },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteBrandAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateBrandAPI(editing.id, values);
    } else {
      await createBrandAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false);
    setEditing(null);
    actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Brand>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getBrandListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建品牌
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑品牌' : '新建品牌'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="品牌名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="firstLetter" label="首字母">
            <Input maxLength={1} />
          </Form.Item>
          <Form.Item name="sort" label="排序">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="showStatus" label="显示状态" initialValue={1}>
            <Select options={[{ value: 0, label: '隐藏' }, { value: 1, label: '显示' }]} />
          </Form.Item>
          <Form.Item name="factoryStatus" label="制造商" initialValue={0}>
            <Select options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
          <Form.Item name="logo" label="Logo URL">
            <Input />
          </Form.Item>
          <Form.Item name="bigPic" label="专区大图">
            <Input />
          </Form.Item>
          <Form.Item name="brandStory" label="品牌故事">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
