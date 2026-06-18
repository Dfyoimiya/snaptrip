import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, Select, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect } from 'react';
import { getResourceListAPI, createResourceAPI, updateResourceAPI, deleteResourceAPI, getResourceCategoriesAPI, createResourceCategoryAPI, deleteResourceCategoryAPI } from '@/services/resource';

export default function ResourcePage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Resource | null>(null);
  const [categories, setCategories] = useState<API.ResourceCategory[]>([]);
  const [form] = Form.useForm();
  const [catName, setCatName] = useState('');

  const fetchCategories = async () => {
    const res = await getResourceCategoriesAPI();
    setCategories(res.data);
  };

  useEffect(() => { fetchCategories(); }, []);

  const columns: ProColumns<API.Resource>[] = [
    { title: '资源名称', dataIndex: 'name' },
    { title: 'URL', dataIndex: 'url', ellipsis: true },
    { title: '描述', dataIndex: 'description', search: false },
    { title: '分类', dataIndex: 'categoryId', search: false,
      render: (v: string) => categories.find(c => c.id === v)?.name || v },
    {
      title: '操作', valueType: 'option',
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteResourceAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateResourceAPI(editing.id, values);
    } else {
      await createResourceAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Resource>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getResourceListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={false}
        pagination={{ pageSize: 20 }}
        toolBarRender={() => [
          <Space key="btns">
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
              新建资源
            </Button>
            <Button onClick={() => setCatModalOpen(true)}>管理分类</Button>
          </Space>,
        ]}
      />
      <Modal title={editing ? '编辑资源' : '新建资源'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="资源名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="url" label="URL"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="categoryId" label="分类">
            <Select allowClear options={categories.map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal title="管理资源分类" open={catModalOpen} onCancel={() => setCatModalOpen(false)} footer={null}>
        <Space style={{ marginBottom: 16 }}>
          <Input placeholder="分类名称" value={catName} onChange={e => setCatName(e.target.value)} />
          <Button type="primary" onClick={async () => {
            if (catName) { await createResourceCategoryAPI({ name: catName }); setCatName(''); fetchCategories(); message.success('已创建'); }
          }}>添加</Button>
        </Space>
        {categories.map(c => (
          <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
            <span>{c.name}</span>
            <Popconfirm title="确认删除?" onConfirm={async () => { await deleteResourceCategoryAPI(c.id); fetchCategories(); }}>
              <a style={{ color: 'red' }}>删除</a>
            </Popconfirm>
          </div>
        ))}
      </Modal>
    </>
  );
}
