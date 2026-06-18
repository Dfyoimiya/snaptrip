import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { useRef } from 'react';
import { useNavigate } from '@umijs/max';
import { getTicketListAPI } from '@/services/cs';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  open: { text: '待处理', color: 'orange' },
  in_progress: { text: '处理中', color: 'blue' },
  resolved: { text: '已解决', color: 'green' },
  closed: { text: '已关闭', color: 'default' },
};

const PRIORITY_MAP: Record<string, { text: string; color: string }> = {
  normal: { text: '普通', color: 'default' },
  urgent: { text: '紧急', color: 'orange' },
  critical: { text: '严重', color: 'red' },
};

export default function TicketList() {
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();

  const columns: ProColumns<API.CsTicket>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 80, valueEnum: { complaint: '投诉', refund: '退款', inquiry: '咨询', other: '其他' } },
    { title: '状态', dataIndex: 'status', width: 100,
      render: (_, r) => <Tag color={STATUS_MAP[r.status]?.color}>{STATUS_MAP[r.status]?.text || r.status}</Tag>,
      valueEnum: { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' },
    },
    { title: '优先级', dataIndex: 'priority', width: 80,
      render: (_, r) => <Tag color={PRIORITY_MAP[r.priority]?.color}>{PRIORITY_MAP[r.priority]?.text || r.priority}</Tag>,
    },
    { title: '会员ID', dataIndex: 'memberId', width: 120, search: false },
    { title: '创建时间', dataIndex: 'createdAt', width: 160, search: false, valueType: 'dateTime' },
    {
      title: '操作', valueType: 'option',
      render: (_, record) => [
        <a key="detail" onClick={() => navigate(`/cs/tickets/${record.id}`)}>详情</a>,
      ],
    },
  ];

  return (
    <ProTable<API.CsTicket>
      columns={columns}
      actionRef={actionRef}
      request={async (params) => {
        const res = await getTicketListAPI(params as Record<string, unknown>);
        return { data: res.data.items, total: res.data.total, success: true };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      pagination={{ pageSize: 20 }}
    />
  );
}
