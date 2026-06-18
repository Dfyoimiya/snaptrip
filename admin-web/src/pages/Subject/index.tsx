import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, Select } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getSubjectListAPI, createSubjectAPI, updateSubjectAPI, deleteSubjectAPI } from '@/services/cms';

export default function SubjectPage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.Subject | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.Subject>[] = [
    { title: '标题', dataIndex: 'title' },
    { title: '分类', dataIndex: 'categoryName', width: 120 },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: '隐藏', 1: { text: '显示', status: 'Success' } } },
    { title: '推荐', dataIndex: 'recommendStatus', width: 80, valueEnum: { 0: '否', 1: { text: '是', status: 'Processing' } } },
    { title: '创建时间', dataIndex: 'createdAt', search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteSubjectAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateSubjectAPI(editing.id, values);
    } else {
      await createSubjectAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.Subject>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getSubjectListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建专题
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑专题' : '新建专题'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="summary" label="摘要"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="pic" label="图片URL"><Input /></Form.Item>
          <Form.Item name="content" label="内容"><Input.TextArea rows={6} /></Form.Item>
          <Form.Item name="categoryName" label="分类"><Input /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 0, label: '隐藏' }, { value: 1, label: '显示' }]} />
          </Form.Item>
          <Form.Item name="recommendStatus" label="推荐" initialValue={0}>
            <Select options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
