import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, Select, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect } from 'react';
import { getAdminListAPI, registerAdminAPI, updateAdminAPI, deleteAdminAPI } from '@/services/admin';
import { getRoleListAllAPI } from '@/services/role';

export default function AdminPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.AdminUser | null>(null);
  const [roles, setRoles] = useState<API.Role[]>([]);
  const [form] = Form.useForm();

  useEffect(() => { getRoleListAllAPI().then(res => setRoles(res.data)); }, []);

  const columns: ProColumns<API.AdminUser>[] = [
    { title: '邮箱', dataIndex: 'email' },
    { title: '状态', dataIndex: 'isActive', width: 80, render: (_, r) => <Tag color={r.isActive ? 'green' : 'red'}>{r.isActive ? '启用' : '禁用'}</Tag> },
    { title: '角色', dataIndex: 'roles', search: false, render: (_, r) => (r.roles || []).map(rl => <Tag key={rl.id}>{rl.name}</Tag>) },
    { title: '创建时间', dataIndex: 'createdAt', search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option',
      render: (_, record) => [
        <a key="edit" onClick={() => {
          setEditing(record);
          form.setFieldsValue({ ...record, roleIds: (record.roles || []).map(r => r.id) });
          setModalOpen(true);
        }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteAdminAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateAdminAPI(editing.id, values);
    } else {
      await registerAdminAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.AdminUser>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getAdminListAPI(params as Record<string, number>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={false}
        pagination={{ pageSize: 20 }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            注册管理员
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑管理员' : '注册管理员'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }} width={500}>
        <Form form={form} layout="vertical">
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}><Input /></Form.Item>
          {!editing && (
            <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}><Input.Password /></Form.Item>
          )}
          {editing && (
            <Form.Item name="password" label="密码 (留空不修改)"><Input.Password /></Form.Item>
          )}
          <Form.Item name="roleIds" label="角色">
            <Select mode="multiple" allowClear options={roles.map(r => ({ value: r.id, label: r.name }))} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
