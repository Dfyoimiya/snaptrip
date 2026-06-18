import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Popconfirm, Space } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getCategoryTreeAPI, createCategoryAPI, updateCategoryAPI, deleteCategoryAPI } from '@/services/category';

export default function CategoryPage() {
  const [tree, setTree] = useState<API.CategoryTree[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Category | null>(null);
  const [parentId, setParentId] = useState<string | undefined>();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const fetchTree = async () => {
    setLoading(true);
    try {
      const res = await getCategoryTreeAPI();
      setTree(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTree(); }, []);

  const flatten = (nodes: API.CategoryTree[], depth = 0): (API.CategoryTree & { depth: number })[] =>
    nodes.flatMap((n) => [{ ...n, depth }, ...flatten(n.children, depth + 1)]);

  const columns = [
    { title: '分类名称', dataIndex: 'name', render: (v: string, r: { depth: number }) => `${'　'.repeat(r.depth)}${v}` },
    { title: '层级', dataIndex: 'level', width: 60 },
    { title: '排序', dataIndex: 'sort', width: 60 },
    { title: '导航', dataIndex: 'navStatus', width: 60, render: (v: number) => v ? '是' : '否' },
    { title: '显示', dataIndex: 'showStatus', width: 60, render: (v: number) => v ? '是' : '否' },
    {
      title: '操作', width: 200, render: (_: unknown, record: API.Category) => (
        <Space>
          <a onClick={() => { setEditing(record); form.setFieldsValue(record); setParentId(undefined); setModalOpen(true); }}>编辑</a>
          <a onClick={() => { setEditing(null); form.resetFields(); setParentId(record.id); setModalOpen(true); }}>添加子分类</a>
          <Popconfirm title="确认删除?" onConfirm={async () => { await deleteCategoryAPI(record.id); message.success('已删除'); fetchTree(); }}>
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
      await updateCategoryAPI(editing.id, values);
    } else {
      await createCategoryAPI(values);
    }
    message.success('保存成功');
    setModalOpen(false);
    fetchTree();
  };

  return (
    <div style={{ padding: 24 }}>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => { setEditing(null); form.resetFields(); setParentId(undefined); setModalOpen(true); }}>
        新建分类
      </Button>
      <Table columns={columns} dataSource={flatten(tree)} rowKey="id" loading={loading} pagination={false} />
      <Modal title={editing ? '编辑分类' : '新建分类'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="分类名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="sort" label="排序">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="navStatus" label="导航显示" initialValue={1}>
            <Select options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
          <Form.Item name="showStatus" label="显示状态" initialValue={1}>
            <Select options={[{ value: 0, label: '隐藏' }, { value: 1, label: '显示' }]} />
          </Form.Item>
          <Form.Item name="keywords" label="SEO关键词">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
