import { useEffect, useState, useRef } from 'react';
import { Card, Descriptions, Tag, Spin, Input, Button, List, Select, message, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useParams } from '@umijs/max';
import { getTicketDetailAPI, getTicketMessagesAPI, sendTicketMessageAPI, assignTicketAPI, resolveTicketAPI } from '@/services/cs';
import dayjs from 'dayjs';

const STATUS_MAP: Record<string, string> = { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' };

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const [ticket, setTicket] = useState<API.CsTicket | null>(null);
  const [messages, setMessages] = useState<API.CsMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [tRes, mRes] = await Promise.all([getTicketDetailAPI(id), getTicketMessagesAPI(id)]);
      setTicket(tRes.data);
      setMessages(mRes.data.messages);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [id]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !id) return;
    await sendTicketMessageAPI(id, { content: input });
    setInput('');
    fetchData();
  };

  if (loading) return <Spin style={{ display: 'block', margin: '100px auto' }} />;
  if (!ticket) return null;

  return (
    <div style={{ padding: 24 }}>
      <Card title={ticket.title}
        extra={
          <Space>
            <Tag color={STATUS_MAP[ticket.status] === '待处理' ? 'orange' : STATUS_MAP[ticket.status] === '处理中' ? 'blue' : 'green'}>
              {STATUS_MAP[ticket.status]}
            </Tag>
            {ticket.status === 'open' && (
              <Button size="small" onClick={async () => { await assignTicketAPI(id!, { action: 'claim' }); fetchData(); }}>认领</Button>
            )}
            {ticket.status === 'in_progress' && (
              <Button size="small" type="primary" onClick={async () => {
                await resolveTicketAPI(id!, { resolution: '已处理' }); fetchData();
              }}>解决</Button>
            )}
          </Space>
        }
      >
        <Descriptions column={2} size="small">
          <Descriptions.Item label="类型">{ticket.type}</Descriptions.Item>
          <Descriptions.Item label="优先级"><Tag>{ticket.priority}</Tag></Descriptions.Item>
          <Descriptions.Item label="会员ID">{ticket.memberId}</Descriptions.Item>
          <Descriptions.Item label="订单ID">{ticket.orderId || '-'}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{ticket.description || '-'}</Descriptions.Item>
          {ticket.resolution && <Descriptions.Item label="处理结果" span={2}>{ticket.resolution}</Descriptions.Item>}
          <Descriptions.Item label="创建时间">{ticket.createdAt ? dayjs(ticket.createdAt).format('YYYY-MM-DD HH:mm') : '-'}</Descriptions.Item>
          <Descriptions.Item label="SLA 截止">{ticket.slaDeadline ? dayjs(ticket.slaDeadline).format('YYYY-MM-DD HH:mm') : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="聊天记录" style={{ marginTop: 16 }}>
        <div ref={listRef} style={{ maxHeight: 400, overflowY: 'auto', marginBottom: 16 }}>
          {messages.map((m) => (
            <div key={m.id} style={{ marginBottom: 12, textAlign: m.senderType === 'agent' ? 'right' : 'left' }}>
              <div style={{ display: 'inline-block', padding: '8px 16px', borderRadius: 8, background: m.senderType === 'agent' ? '#1677ff' : '#f0f0f0', color: m.senderType === 'agent' ? '#fff' : '#000', maxWidth: '70%', textAlign: 'left' }}>
                <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>{m.senderType === 'agent' ? '客服' : '用户'} · {dayjs(m.createdAt).format('HH:mm')}</div>
                {m.content}
              </div>
            </div>
          ))}
        </div>
        <Input.Search enterButton={<SendOutlined />} value={input} onChange={e => setInput(e.target.value)} onSearch={handleSend} placeholder="输入消息..." />
      </Card>
    </div>
  );
}
