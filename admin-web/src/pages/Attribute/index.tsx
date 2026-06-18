import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Modal, Form, Input, InputNumber, Select } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { getAttributeListAPI, createAttributeAPI, updateAttributeAPI, deleteAttributeAPI } from '@/services/attribute';

export default function AttributePage() {
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<API.ProductAttribute | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.ProductAttribute>[] = [
    { title: '属性名称', dataIndex: 'name' },
    { title: '分类ID', dataIndex: 'categoryId', width: 120, search: false },
    { title: '类型', dataIndex: 'attrType', width: 80, valueEnum: { 0: '规格', 1: '参数' } },
    { title: '输入类型', dataIndex: 'inputType', width: 80, valueEnum: { 0: '手动', 1: '单选', 2: '多选' } },
    { title: '可选值', dataIndex: 'inputList', ellipsis: true, search: false },
    { title: '排序', dataIndex: 'sort', width: 80, search: false },
    {
      title: '操作', valueType: 'option', width: 200,
      render: (_, record) => [
        <a key="edit" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</a>,
        <Popconfirm key="del" title="确认删除?" onConfirm={async () => {
          await deleteAttributeAPI(record.id); message.success('已删除'); actionRef.current?.reload();
        }}><a style={{ color: 'red' }}>删除</a></Popconfirm>,
      ],
    },
  ];

  const handleSave = async () => {
    const values = form.getFieldsValue();
    if (editing?.id) {
      await updateAttributeAPI(editing.id, values);
    } else {
      await createAttributeAPI(values);
    }
    message.success(editing?.id ? '已更新' : '已创建');
    setModalOpen(false); setEditing(null); actionRef.current?.reload();
  };

  return (
    <>
      <ProTable<API.ProductAttribute>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const res = await getAttributeListAPI(params as Record<string, unknown>);
          return { data: res.data.items, total: res.data.total, success: true };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>
            新建属性
          </Button>,
        ]}
      />
      <Modal title={editing ? '编辑属性' : '新建属性'} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditing(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="categoryId" label="分类ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="属性名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="attrType" label="属性类型" initialValue={0}>
            <Select options={[{ value: 0, label: '规格' }, { value: 1, label: '参数' }]} />
          </Form.Item>
          <Form.Item name="inputType" label="输入类型" initialValue={0}>
            <Select options={[{ value: 0, label: '手动输入' }, { value: 1, label: '单选' }, { value: 2, label: '多选' }]} />
          </Form.Item>
          <Form.Item name="inputList" label="可选值(逗号分隔)"><Input /></Form.Item>
          <Form.Item name="sort" label="排序"><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
