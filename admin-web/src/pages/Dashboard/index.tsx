import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table } from 'antd';
import { ShoppingCartOutlined, DollarOutlined, UserAddOutlined, FileProtectOutlined } from '@ant-design/icons';
import { getDashboardAPI } from '@/services/dashboard';
// Charts can be added with echarts-for-react or @ant-design/charts

export default function DashboardPage() {
  const [data, setData] = useState<API.DashboardData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getDashboardAPI();
      setData(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const columnChart = {
    tooltip: { trigger: 'axis' },
    xAxis: { data: data?.weekDays || [], type: 'category' },
    yAxis: { type: 'value' },
    series: [{ data: data?.weekSales || [], type: 'bar', color: '#1677ff' }],
  };

  const orderCols = [
    { title: '订单编号', dataIndex: 'orderSn', key: 'orderSn' },
    { title: '用户', dataIndex: 'memberUsername', key: 'memberUsername' },
    { title: '金额', dataIndex: 'payAmount', key: 'payAmount', render: (v: number) => `¥${v}` },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (v: number) => ['待付款', '已付款', '已发货', '已收货', '已完成', '已关闭'][v] || v,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="今日订单" value={data?.todayOrders || 0} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="今日营收" value={data?.todayRevenue || 0} prefix={<DollarOutlined />} precision={2} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="新会员" value={data?.newMembers || 0} prefix={<UserAddOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic title="待处理退货" value={data?.pendingReturns || 0} prefix={<FileProtectOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="近7天销售趋势">
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              {data?.weekSales?.join(', ') || 'No data'}
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="最新订单">
            <Table
              columns={orderCols}
              dataSource={data?.latestOrders || []}
              rowKey="id"
              size="small"
              pagination={false}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
