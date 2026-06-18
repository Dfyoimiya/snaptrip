import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, message, Popconfirm } from 'antd';
import { useRef } from 'react';
import { getMemberListAPI, toggleMemberStatusAPI } from '@/services/member';

export default function MemberPage() {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<API.Member>[] = [
    { title: 'ID', dataIndex: 'id', width: 100, search: false },
    { title: '邮箱', dataIndex: 'email' },
    {
      title: '状态', dataIndex: 'isActive', width: 80,
      render: (_, r) => <Tag color={r.isActive ? 'green' : 'red'}>{r.isActive ? '启用' : '封禁'}</Tag>,
      valueEnum: { true: '启用', false: '封禁' },
    },
    { title: '注册时间', dataIndex: 'createdAt', search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option', width: 150,
      render: (_, record) => [
        <Popconfirm key="toggle" title={`确认${record.isActive ? '封禁' : '启用'}?`}
          onConfirm={async () => {
            await toggleMemberStatusAPI(record.id, !record.isActive);
            message.success('操作成功');
            actionRef.current?.reload();
          }}
        >
          <a>{record.isActive ? '封禁' : '启用'}</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <ProTable<API.Member>
      columns={columns}
      actionRef={actionRef}
      request={async (params) => {
        const res = await getMemberListAPI(params as Record<string, unknown>);
        return { data: res.data.items, total: res.data.total, success: true };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      pagination={{ pageSize: 20 }}
    />
  );
}
