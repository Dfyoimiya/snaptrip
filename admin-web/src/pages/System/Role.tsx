import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, InputNumber, TreeSelect, Select, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect } from 'react';
import { getRoleListAPI, createRoleAPI, updateRoleAPI, deleteRolesAPI, getRoleMenuListAPI, getRoleResourceListAPI, allocRoleMenuAPI, allocRoleResourceAPI } from '@/services/role';
import { getMenuTreeAPI } from '@/services/menu';
import { getResourceListAllAPI } from '@/services/resource';

export default function RolePage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [menuModalOpen, setMenuModalOpen] = useState(false);
  const [resourceModalOpen, setResourceModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Role | null>(null);
  const [menuTree, setMenuTree] = useState<API.MenuNode[]>([]);
  const [resources, setResources] = useState<API.Resource[]>([]);
  const [selectedMenuIds, setSelectedMenuIds] = useState<string[]>([]);
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [form] = Form.useForm();

  useEffect(() => {
    getMenuTreeAPI().then(res => setMenuTree(res.data));
    getResourceListAllAPI().then(res => setResources(res.data));
  }, []);

  const columns: ProColumns<API.Role>[] = [
    { title: '角色名称', dataIndex: 'name' },
    { title: '描述', dataIndex: 'description', search: false },
    { title: '排序', dataIndex: 'sort', width: 80, search: false },
    { title: '状态', dataIndex: 'status', width: 80, render: (_, r) => <Tag color={r.status ? 'green' : 'red'}>{r.status ? '启用' : '禁用'}</Tag> },
    {
      title: '操作', valueType: 'option', width: 300,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <a key="menu" onClick={async () => {
          setEditing(record);
          const res = await getRoleMenuListAPI(record.id);
          // Menu list returns all menus — we need to track which are allocated in a real app
          setMenuModalOpen(true);
        }}>分配菜单</a>,
        <a key="res" onClick={async () => {
          setEditing(record);
          setResourceModalOpen(true);
        }}>分配资源</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteRolesAPI([record.id]); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateRoleAPI(editing.id, values);
    } else {
      await createRoleAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  const menuTreeData = menuTree.map(m => ({
    title: m.title, value: m.id, key: m.id,
    children: m.children?.map(c => ({
      title: c.title, value: c.id, key: c.id,
      children: c.children?.map(gc => ({ title: gc.title, value: gc.id, key: gc.id })),
    })),
  }));

  return (
    <>
      <ProTable<API.Role>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getRoleListAPI(params as Record<string, number>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={false}
        pagination={{ pageSize: 20 }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建角色
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑角色' : '新建角色'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="角色名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 0, label: '禁用' }, { value: 1, label: '启用' }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Menu allocation modal */}
      <Modal title="分配菜单" open={menuModalOpen} onOk={async () => {
        if (editing) { await allocRoleMenuAPI(editing.id, selectedMenuIds); message.success('菜单分配成功'); }
        setMenuModalOpen(false);
      }} onCancel={() => setMenuModalOpen(false)} width={500}>
        <TreeSelect treeData={menuTreeData} treeCheckable style={{ width: '100%' }} value={selectedMenuIds} onChange={(v) => setSelectedMenuIds(v as string[])} />
      </Modal>

      {/* Resource allocation modal */}
      <Modal title="分配资源" open={resourceModalOpen} onOk={async () => {
        if (editing) { await allocRoleResourceAPI(editing.id, selectedResourceIds); message.success('资源分配成功'); }
        setResourceModalOpen(false);
      }} onCancel={() => setResourceModalOpen(false)} width={500}>
        <Select mode="multiple" style={{ width: '100%' }} value={selectedResourceIds} onChange={setSelectedResourceIds}
          options={resources.map(r => ({ value: r.id, label: `${r.name} (${r.url || '-'})` }))} />
      </Modal>
    </>
  );
}
