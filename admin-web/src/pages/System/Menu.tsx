import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Popconfirm, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getMenuTreeAPI, createMenuAPI, updateMenuAPI, deleteMenuAPI } from '@/services/menu';

export default function MenuPage() {
  const [tree, setTree] = useState<API.MenuNode[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.MenuNode | null>(null);
  const [parentId, setParentId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const fetchTree = async () => {
    setLoading(true);
    try { const res = await getMenuTreeAPI(); setTree(res.data); } finally { setLoading(false); }
  };

  useEffect(() => { fetchTree(); }, []);

  const flatten = (nodes: API.MenuNode[], depth = 0): (API.MenuNode & { depth: number })[] =>
    nodes.flatMap((n) => [{ ...n, depth }, ...flatten(n.children || [], depth + 1)]);

  const columns = [
    { title: '菜单名称', dataIndex: 'title', render: (v: string, r: { depth: number }) => `${'　'.repeat(r.depth)}${v}` },
    { title: '路由名称', dataIndex: 'name' },
    { title: '图标', dataIndex: 'icon' },
    { title: '排序', dataIndex: 'sort', width: 60 },
    { title: '隐藏', dataIndex: 'hidden', width: 60, render: (v: number) => v ? '是' : '否' },
    {
      title: '操作', render: (_: unknown, r: API.MenuNode) => (
        <Space>
          <a onClick={() => { setEditing(r); form.setFieldsValue(r); setParentId(null); setModalOpen(true); }}>编辑</a>
          <a onClick={() => { setEditing(null); form.resetFields(); setParentId(r.id); setModalOpen(true); }}>添加子菜单</a>
          <Popconfirm title="确认删除?" onConfirm={async () => { await deleteMenuAPI(r.id); message.success('已删除'); fetchTree(); }}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (parentId) values.parentId = parentId;
    if (editing?.id) {
      await updateMenuAPI(editing.id, values);
    } else {
      await createMenuAPI(values);
    }
    message.success('保存成功');
    setModalOpen(false); fetchTree();
  };

  return (
    <div style={{ padding: 24 }}>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }}
        onClick={() => { setEditing(null); form.resetFields(); setParentId(null); setModalOpen(true); }}>
        新建菜单
      </Button>
      <Table columns={columns} dataSource={flatten(tree)} rowKey="id" loading={loading} pagination={false} />
      <Modal title={editing ? '编辑菜单' : '新建菜单'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="路由名称"><Input /></Form.Item>
          <Form.Item name="icon" label="图标"><Input /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
          <Form.Item name="hidden" label="是否隐藏" initialValue={0}>
            <Select options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
