<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Goods, Document, User, ShoppingCart,
  TrendCharts, Setting, Lock, Collection,
  Money, Box, CircleCheck, Warning,
  HomeFilled, ArrowUp, ArrowDown,
} from '@element-plus/icons-vue'

const router = useRouter()
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早安'
  if (hour < 18) return '下午好'
  return '晚上好'
})

// 核心统计
const coreStats = ref([
  { label: '今日订单', value: 128, change: 12.5, up: true, icon: Document, color: '#165dff', bg: '#e8f4ff' },
  { label: '今日销售额', value: '¥25,680', change: 8.2, up: true, icon: Money, color: '#00b42a', bg: '#e8ffea' },
  { label: '今日新增会员', value: 36, change: -3.1, up: false, icon: User, color: '#f7ba1e', bg: '#fff7e8' },
  { label: '待处理退货', value: 8, change: 2.0, up: true, icon: Warning, color: '#f53f3f', bg: '#ffece8' },
])

// 快捷导航
const shortcuts = ref([
  { title: '商品列表', icon: Goods, path: '/pms/product', color: '#165dff' },
  { title: '订单列表', icon: Document, path: '/oms/order', color: '#f7ba1e' },
  { title: '会员列表', icon: User, path: '/ums/member', color: '#f53f3f' },
  { title: '优惠券', icon: Collection, path: '/sms/coupon', color: '#722ed1' },
  { title: '品牌管理', icon: Goods, path: '/pms/brand', color: '#14c9c9' },
  { title: '秒杀活动', icon: ShoppingCart, path: '/sms/flash', color: '#ff7d00' },
])

// 订单状态统计
const orderStatusStats = ref([
  { label: '待付款', count: 23, type: 'warning' },
  { label: '待发货', count: 45, type: 'primary' },
  { label: '已发货', count: 68, type: 'success' },
  { label: '已完成', count: 1256, type: 'info' },
  { label: '退款中', count: 8, type: 'danger' },
])

// 待办事项
const todos = ref([
  { title: '审核新上架商品 15 件', priority: 'high', done: false },
  { title: '处理退货申请 3 单', priority: 'high', done: false },
  { title: '核对昨日财务报表', priority: 'high', done: false },
  { title: '更新商品分类排序', priority: 'medium', done: true },
  { title: '编写运营周报', priority: 'low', done: false },
  { title: '检查库存预警商品', priority: 'medium', done: false },
])

// 最新订单
const latestOrders = ref([
  { id: 1, orderSn: 'ORD20250602001', member: '张三', amount: 8999, status: 1, statusLabel: '待发货' },
  { id: 2, orderSn: 'ORD20250602002', member: '李四', amount: 3290, status: 2, statusLabel: '已发货' },
  { id: 3, orderSn: 'ORD20250602003', member: '王五', amount: 1599, status: 0, statusLabel: '待付款' },
  { id: 4, orderSn: 'ORD20250602004', member: '赵六', amount: 2599, status: 2, statusLabel: '已发货' },
  { id: 5, orderSn: 'ORD20250602005', member: '钱七', amount: 6999, status: 1, statusLabel: '待发货' },
])

const orderStatusType = (status: number) => {
  const map: Record<number, string> = { 0: 'warning', 1: 'primary', 2: 'success' }
  return map[status] || 'info'
}

// 近7天销售趋势数据
const weekDays = ref(['周一', '周二', '周三', '周四', '周五', '周六', '周日'])
const weekSales = ref([18500, 22300, 19800, 25600, 31200, 28900, 25680])
const maxSales = computed(() => Math.max(...weekSales.value))

// 商品销售排行
const topProducts = ref([
  { name: 'iPhone 15 Pro', sales: 156, amount: 1403844 },
  { name: '华为Mate60 Pro', sales: 128, amount: 895872 },
  { name: '戴森吹风机', sales: 98, amount: 322420 },
  { name: 'AirPods Pro 2', sales: 87, amount: 139113 },
  { name: '索尼WH-1000XM5', sales: 72, amount: 215928 },
])

// 计算柱状图高度百分比
const barHeight = (value: number) => `${Math.max((value / maxSales.value) * 100, 8)}%`

onMounted(() => {
  // 模拟数据加载
})
</script>

<template>
  <div class="home-dashboard">
    <!-- 欢迎横幅 -->
    <el-card class="welcome-card" shadow="never">
      <div class="welcome-content">
        <div class="welcome-left">
          <img src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" class="welcome-avatar" alt="avatar" />
          <div>
            <div class="welcome-title">{{ greeting }}，Admin，开始您一天的工作吧！</div>
            <div class="welcome-subtitle">mall-admin-vue3 后台管理系统</div>
          </div>
        </div>
        <div class="welcome-weather">
          <span style="color: #909399; font-size: 13px">{{ new Date().toLocaleDateString() }} {{ ['周日','周一','周二','周三','周四','周五','周六'][new Date().getDay()] }}</span>
        </div>
      </div>
    </el-card>

    <!-- 核心指标 -->
    <el-row :gutter="12" style="margin-bottom: 12px">
      <el-col :xs="12" :sm="6" v-for="stat in coreStats" :key="stat.label">
        <el-card class="stat-card" shadow="never">
          <div class="stat-main">
            <div class="stat-icon" :style="{ backgroundColor: stat.bg, color: stat.color }">
              <el-icon :size="22"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="stat-change" :class="stat.up ? 'up' : 'down'">
                <el-icon><component :is="stat.up ? ArrowUp : ArrowDown" /></el-icon>
                {{ Math.abs(stat.change) }}%
                <span style="color: #c9cdd4; font-weight: normal">环比</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 中部内容 -->
    <el-row :gutter="12">
      <!-- 左侧：销售趋势 + 排行榜 -->
      <el-col :xs="24" :lg="16">
        <!-- 本周销售趋势 -->
        <el-card shadow="never" style="margin-bottom: 12px">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">本周销售趋势</span>
              <span style="color: #909399; font-size: 13px">单位：元</span>
            </div>
          </template>
          <div class="chart-container">
            <div v-for="(day, i) in weekDays" :key="day" class="chart-bar-wrapper">
              <div class="chart-bar" :style="{ height: barHeight(weekSales[i]) }">
                <span class="chart-bar-value">¥{{ (weekSales[i] / 1000).toFixed(1) }}k</span>
              </div>
              <div class="chart-bar-label">{{ day }}</div>
            </div>
          </div>
        </el-card>

        <!-- 商品销售排行 -->
        <el-card shadow="never">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">商品销售排行 TOP5</span>
            </div>
          </template>
          <div class="product-rank">
            <div v-for="(p, i) in topProducts" :key="p.name" class="rank-row">
              <div class="rank-num" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</div>
              <div class="rank-name">{{ p.name }}</div>
              <el-progress :percentage="Math.round((p.sales / topProducts[0].sales) * 100)" :stroke-width="8" :show-text="false" style="flex: 1" />
              <div class="rank-sales">{{ p.sales }}单</div>
              <div class="rank-amount">¥{{ (p.amount / 10000).toFixed(1) }}万</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：快捷入口 + 订单状态 + 最新订单 + 待办 -->
      <el-col :xs="24" :lg="8">
        <!-- 快捷入口 -->
        <el-card shadow="never" style="margin-bottom: 12px">
          <template #header>
            <span class="panel-title">快捷入口</span>
          </template>
          <div class="shortcut-grid">
            <div v-for="s in shortcuts" :key="s.path" class="shortcut-item" @click="router.push(s.path)">
              <div class="shortcut-icon" :style="{ backgroundColor: s.color + '12', color: s.color }">
                <el-icon :size="20"><component :is="s.icon" /></el-icon>
              </div>
              <span class="shortcut-title">{{ s.title }}</span>
            </div>
          </div>
        </el-card>

        <!-- 订单状态 -->
        <el-card shadow="never" style="margin-bottom: 12px">
          <template #header>
            <span class="panel-title">订单状态</span>
          </template>
          <div class="order-status-grid">
            <div v-for="s in orderStatusStats" :key="s.label" class="order-status-item">
              <div class="order-status-count" :style="{ color: s.type === 'warning' ? '#e6a23c' : s.type === 'primary' ? '#409eff' : s.type === 'success' ? '#67c23a' : s.type === 'danger' ? '#f56c6c' : '#909399' }">
                {{ s.count }}
              </div>
              <el-tag :type="s.type" size="small">{{ s.label }}</el-tag>
            </div>
          </div>
        </el-card>

        <!-- 最新订单 -->
        <el-card shadow="never" style="margin-bottom: 12px">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">最新订单</span>
              <el-button text size="small" @click="router.push('/oms/order')">查看全部</el-button>
            </div>
          </template>
          <div class="latest-orders">
            <div v-for="o in latestOrders" :key="o.id" class="order-row">
              <div>
                <div style="font-size: 13px; font-weight: 500">{{ o.orderSn }}</div>
                <div style="font-size: 12px; color: #909399">{{ o.member }}</div>
              </div>
              <div style="text-align: right">
                <div style="font-size: 14px; font-weight: 600; color: #f56c6c">¥{{ o.amount }}</div>
                <el-tag :type="orderStatusType(o.status)" size="small">{{ o.statusLabel }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 待办 -->
        <el-card shadow="never">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">待办事项</span>
              <el-tag size="small" type="warning">{{ todos.filter(t => !t.done).length }} 待处理</el-tag>
            </div>
          </template>
          <div class="todo-list">
            <div v-for="t in todos" :key="t.title" class="todo-item" :class="{ done: t.done }">
              <el-checkbox v-model="t.done" size="small">
                <span :class="{ 'todo-done': t.done }">{{ t.title }}</span>
              </el-checkbox>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.home-dashboard {
  padding: 12px;

  .welcome-card {
    margin-bottom: 12px;
    border-radius: 8px;
    :deep(.el-card__body) { padding: 16px 20px; }
  }

  .welcome-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .welcome-left {
    display: flex;
    align-items: center;
    gap: 14px;
    .welcome-avatar {
      width: 48px;
      height: 48px;
      border-radius: 50%;
    }
    .welcome-title {
      font-size: 16px;
      font-weight: 600;
      color: #1f2229;
      margin-bottom: 2px;
    }
    .welcome-subtitle {
      font-size: 12px;
      color: #86909c;
    }
  }

  .stat-card {
    border-radius: 8px;
    :deep(.el-card__body) { padding: 16px; }
  }

  .stat-main {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .stat-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .stat-body {
    flex: 1;
    min-width: 0;
  }

  .stat-label {
    font-size: 12px;
    color: #86909c;
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .stat-change {
    font-size: 11px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 2px;
    &.up { color: #67c23a; }
    &.down { color: #f56c6c; }
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2229;
  }

  // 柱状图
  .chart-container {
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    height: 200px;
    padding: 20px 10px 0;
    gap: 12px;
  }

  .chart-bar-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    height: 100%;
  }

  .chart-bar {
    width: 100%;
    max-width: 60px;
    background: linear-gradient(180deg, #409eff, #79bbff);
    border-radius: 6px 6px 0 0;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 6px;
    transition: all 0.3s;
    min-height: 8%;
    position: relative;

    &:hover {
      background: linear-gradient(180deg, #165dff, #409eff);
    }
  }

  .chart-bar-value {
    font-size: 10px;
    color: #fff;
    font-weight: 600;
    white-space: nowrap;
  }

  .chart-bar-label {
    margin-top: 8px;
    font-size: 12px;
    color: #86909c;
  }

  // 商品排行
  .product-rank {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .rank-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .rank-num {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #f2f3f5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    color: #86909c;
    flex-shrink: 0;

    &.top {
      background: #165dff;
      color: #fff;
    }
  }

  .rank-name {
    width: 130px;
    font-size: 13px;
    color: #1f2229;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
  }

  .rank-sales {
    width: 50px;
    text-align: right;
    font-size: 12px;
    color: #606266;
    flex-shrink: 0;
  }

  .rank-amount {
    width: 70px;
    text-align: right;
    font-size: 12px;
    color: #f56c6c;
    font-weight: 500;
    flex-shrink: 0;
  }

  // 快捷入口
  .shortcut-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .shortcut-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 14px 8px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;

    &:hover {
      background: #f7f8fa;
      border-color: #e5e6eb;
    }
  }

  .shortcut-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .shortcut-title {
    font-size: 12px;
    color: #4e5969;
  }

  // 订单状态
  .order-status-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
  }

  .order-status-item {
    text-align: center;
    padding: 8px 0;
  }

  .order-status-count {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  // 最新订单
  .latest-orders {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .order-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f7f8fa;

    &:last-child {
      border-bottom: none;
    }
  }

  // 待办
  .todo-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .todo-item {
    padding: 6px 0;
    border-bottom: 1px solid #f7f8fa;

    &:last-child {
      border-bottom: none;
    }

    .todo-done {
      text-decoration: line-through;
      color: #c9cdd4;
    }
  }

  :deep(.el-card__header) {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  :deep(.el-card__body) {
    padding: 14px 16px;
  }
}
</style>
