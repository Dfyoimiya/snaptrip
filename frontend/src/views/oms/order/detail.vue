<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, Clock, CircleCheckFilled, Van, WalletFilled, Postcard } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { getOrderDetailByIdAPI, orderUpdateDeliveryAPI } from '@/apis/order'
import type { OmsOrderDetail, OmsOrderItem, OmsOrderOperateHistory } from '@/types/order'

const route = useRoute()
const router = useRouter()
const orderId = ref('')
const loading = ref(true)
const order = ref<OmsOrderDetail | null>(null)

// ============================================================
// 状态常量
// ============================================================
const STATUS = {
  PENDING_PAYMENT: 0,
  PAID: 1,
  DELIVERED: 2,
  RECEIVED: 3,
  COMPLETED: 4,
  CLOSED: 5,
  REFUNDING: 6,
  REFUNDED: 7,
} as const

const STATUS_LABEL: Record<number, string> = {
  [STATUS.PENDING_PAYMENT]: '待付款',
  [STATUS.PAID]: '待发货',
  [STATUS.DELIVERED]: '已发货',
  [STATUS.RECEIVED]: '已收货',
  [STATUS.COMPLETED]: '已完成',
  [STATUS.CLOSED]: '已关闭',
  [STATUS.REFUNDING]: '退款中',
  [STATUS.REFUNDED]: '已退款',
}

const STATUS_BANNER: Record<number, { title: string; sub: string; icon: any; color: string }> = {
  [STATUS.PENDING_PAYMENT]: {
    title: '等待买家付款',
    sub: '买家拍下商品后还未付款，订单将在超时后自动关闭',
    icon: Clock,
    color: '#f59e0b',
  },
  [STATUS.PAID]: {
    title: '买家已付款',
    sub: '买家已支付成功，请尽快发货',
    icon: WalletFilled,
    color: '#e75a1c',
  },
  [STATUS.DELIVERED]: {
    title: '卖家已发货',
    sub: '商品已发出，等待买家确认收货',
    icon: Van,
    color: '#3b82f6',
  },
  [STATUS.RECEIVED]: {
    title: '买家已确认收货',
    sub: '交易即将完成',
    icon: CircleCheckFilled,
    color: '#22c55e',
  },
  [STATUS.COMPLETED]: {
    title: '交易已完成',
    sub: '订单已完成，感谢您的购买',
    icon: CircleCheckFilled,
    color: '#22c55e',
  },
  [STATUS.CLOSED]: {
    title: '交易已关闭',
    sub: '该订单已被关闭',
    icon: WarningFilled,
    color: '#909399',
  },
  [STATUS.REFUNDING]: {
    title: '退款处理中',
    sub: '买家申请退款，请及时处理',
    icon: WarningFilled,
    color: '#f59e0b',
  },
  [STATUS.REFUNDED]: {
    title: '已退款',
    sub: '退款已完成',
    icon: CircleCheckFilled,
    color: '#909399',
  },
}

// ============================================================
// 步骤条
// ============================================================
const stepItems = ['拍下宝贝', '买家付款', '卖家发货', '确认收货', '交易完成']

const activeStep = computed(() => {
  const s = order.value?.status ?? 0
  if (s === STATUS.CLOSED) return -1
  if (s === STATUS.REFUNDING || s === STATUS.REFUNDED) return 1 // 停在付款后
  if (s >= STATUS.COMPLETED) return 4
  return s
})

const stepStatus = computed(() => {
  const s = order.value?.status
  if (s === STATUS.CLOSED) return 'exception'
  if (s === STATUS.REFUNDING || s === STATUS.REFUNDED) return 'exception'
  return 'success'
})

// ============================================================
// 时间线提取（从操作日志和订单字段）
// ============================================================
interface TimeNode {
  label: string
  time: string | null
}
const timeline = computed<TimeNode[]>(() => {
  const o = order.value
  if (!o) return []
  return [
    { label: '拍下时间', time: o.createdAt || null },
    { label: '付款时间', time: (o as any).paymentTime || null },
    { label: '发货时间', time: o.deliveryTime || null },
    { label: '收货时间', time: (o as any).receiveTime || null },
  ]
})

// ============================================================
// 发货弹窗
// ============================================================
const deliveryVisible = ref(false)
const deliveryForm = ref({ deliveryCompany: '', deliverySn: '' })

// ============================================================
// 数据加载
// ============================================================
async function loadOrder() {
  loading.value = true
  try {
    const res = await getOrderDetailByIdAPI(orderId.value)
    const detail = (res as any).data || res
    order.value = {
      ...detail,
      items: detail.orderItemList || detail.items || [],
      historyList: detail.logs || detail.historyList || [],
    }
  } catch {
    ElMessage.error('加载订单详情失败')
    order.value = null
  } finally {
    loading.value = false
  }
}

function handleBack() {
  router.back()
}

// ============================================================
// 操作按钮
// ============================================================
async function handleDelivery() {
  if (!deliveryForm.value.deliveryCompany || !deliveryForm.value.deliverySn) {
    ElMessage.warning('请填写物流公司和物流单号')
    return
  }
  try {
    await orderUpdateDeliveryAPI([
      { orderId: orderId.value, ...deliveryForm.value },
    ] as any)
    ElMessage.success('发货成功')
    deliveryVisible.value = false
    loadOrder()
  } catch {
    ElMessage.error('发货失败')
  }
}

function handleCloseOrder() {
  ElMessageBox.prompt('请输入关闭原因', '关闭订单', { confirmButtonText: '确定', cancelButtonText: '取消' })
    .then(async ({ value }) => {
      const { orderUpdateCloseAPI } = await import('@/apis/order')
      await orderUpdateCloseAPI(orderId.value, value || '')
      ElMessage.success('订单已关闭')
      loadOrder()
    })
    .catch(() => {})
}

function handleRefund() {
  ElMessageBox.prompt('请输入退款备注', '确认退款', { confirmButtonText: '确定', cancelButtonText: '取消' })
    .then(async ({ value }) => {
      // Use the refund API — POST /admin/orders/{id}/refund
      const request = (await import('@/utils/request')).default
      await request({
        url: `/admin/orders/${orderId.value}/refund`,
        method: 'post',
        params: { note: value || '' },
      })
      ElMessage.success('退款成功')
      loadOrder()
    })
    .catch(() => {})
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  const id = route.query.id as string
  if (!id) {
    ElMessage.error('订单ID不能为空')
    router.replace('/oms/order')
    return
  }
  orderId.value = id
  loadOrder()
})

watch(() => route.query.id, (newId) => {
  if (newId) {
    orderId.value = newId as string
    loadOrder()
  }
})

// ============================================================
// 金额计算
// ============================================================
const itemTotal = computed(() => {
  return order.value?.items?.reduce((sum, item) => sum + (item.price || 0) * (item.quantity || 0), 0) ?? 0
})

// 安全获取当前状态 banner（避免模板中 order.status undefined 类型错误）
const currentBanner = computed(() => {
  const s = order.value?.status ?? 0
  return STATUS_BANNER[s]
})
</script>

<template>
  <div class="order-detail" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="top-bar">
      <el-button text @click="handleBack" class="back-btn">
        <el-icon><ArrowLeft /></el-icon>返回订单列表
      </el-button>
      <div class="order-sn-header">
        <span class="sn-label">订单号：{{ order?.orderSn }}</span>
      </div>
    </div>

    <div class="main-layout" v-if="order">
      <!-- ========== 左侧 2/3 ========== -->
      <div class="left-panel">
        <!-- 状态步骤条 -->
        <div class="steps-card">
          <div class="steps-card-header">
            <span class="steps-card-title">订单状态</span>
            <el-tag
              v-if="order.status === STATUS.CLOSED"
              type="info"
              size="large"
            >已关闭</el-tag>
            <el-tag
              v-else-if="order.status === STATUS.REFUNDING"
              type="warning"
              size="large"
            >退款中</el-tag>
            <el-tag
              v-else-if="order.status === STATUS.REFUNDED"
              type="info"
              size="large"
            >已退款</el-tag>
          </div>

          <div class="steps-wrapper" v-if="order.status !== STATUS.CLOSED && order.status !== STATUS.REFUNDED">
            <el-steps
              :active="activeStep"
              :status="stepStatus"
              align-center
              finish-status="success"
            >
              <el-step
                v-for="(s, i) in stepItems"
                :key="i"
                :title="s"
                :description="timeline[i]?.time ? formatDateTime(timeline[i].time!) : ''"
              />
            </el-steps>
          </div>

          <div class="closed-banner" v-if="order.status === STATUS.CLOSED">
            <el-icon :size="48" color="#909399"><WarningFilled /></el-icon>
            <span class="closed-text">交易已关闭</span>
          </div>

          <div class="refunded-banner" v-if="order.status === STATUS.REFUNDED">
            <el-icon :size="48" color="#909399"><CircleCheckFilled /></el-icon>
            <span class="refunded-text">已退款</span>
          </div>
        </div>

        <!-- 当前状态 Banner -->
        <div class="status-banner" :style="{ borderLeftColor: currentBanner?.color || '#3b82f6' }">
          <div class="banner-icon" :style="{ color: currentBanner?.color || '#3b82f6' }">
            <el-icon :size="36">
              <component :is="currentBanner?.icon" />
            </el-icon>
          </div>
          <div class="banner-text">
            <div class="banner-title" :style="{ color: currentBanner?.color || '#3b82f6' }">
              {{ currentBanner?.title || '--' }}
            </div>
            <div class="banner-sub">{{ currentBanner?.sub || '' }}</div>
          </div>
          <!-- 倒计时/超时提示 (待付款) -->
          <div v-if="order.status === STATUS.PENDING_PAYMENT" class="banner-extra">
            <el-icon :size="14" style="margin-right:4px"><Clock /></el-icon>
            <span style="font-size:13px">超时后将自动关闭</span>
          </div>
        </div>

        <!-- 物流信息 (已发货/已收货/已完成) -->
        <div class="info-row" v-if="order.deliveryCompany && (order.status ?? 0) >= STATUS.DELIVERED">
          <div class="info-row-left">
            <el-icon :size="20" color="#3b82f6"><Postcard /></el-icon>
            <div class="info-row-text">
              <span class="info-label">物流公司</span>
              <span class="info-value">{{ order.deliveryCompany }}</span>
            </div>
          </div>
          <div class="info-row-right">
            <span class="info-label">运单号</span>
            <span class="info-value mono">{{ order.deliverySn }}</span>
          </div>
        </div>

        <!-- 店铺信息 -->
        <div class="shop-bar">
          <div class="shop-avatar">店</div>
          <span class="shop-name">{{ order.memberUsername || '店铺' }}</span>
          <el-icon :size="12" color="#999"><ArrowRight /></el-icon>
        </div>

        <!-- 商品列表 (横向) -->
        <div class="product-list">
          <div class="product-row" v-for="item in order.items" :key="item.id">
            <div class="product-image">
              <img v-if="item.productPic" :src="item.productPic" :alt="item.productName" />
              <div v-else class="product-image-placeholder">
                <el-icon :size="28"><Picture /></el-icon>
              </div>
            </div>
            <div class="product-info">
              <a class="product-name" href="javascript:void(0)">
                {{ item.productName }}
              </a>
              <div class="product-spec" v-if="item.spec">{{ item.spec }}</div>
            </div>
            <div class="product-price">￥{{ item.price }}</div>
            <div class="product-quantity">×{{ item.quantity }}</div>
            <div class="product-subtotal">￥{{ (item.price || 0) * (item.quantity || 0) }}</div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-bar" v-if="order.status === STATUS.PENDING_PAYMENT || order.status === STATUS.PAID || order.status === STATUS.DELIVERED || order.status === STATUS.REFUNDING">
          <el-button
            v-if="order.status === STATUS.PAID"
            type="primary"
            size="large"
            @click="deliveryVisible = true"
            style="background: #e75a1c; border-color: #e75a1c"
          >
            发货
          </el-button>
          <el-button
            v-if="order.status === STATUS.PENDING_PAYMENT"
            type="danger"
            size="large"
            @click="handleCloseOrder"
          >
            关闭订单
          </el-button>
          <el-button
            v-if="order.status === STATUS.REFUNDING"
            type="primary"
            size="large"
            @click="handleRefund"
          >
            确认退款
          </el-button>
        </div>
      </div>

      <!-- ========== 右侧 1/3 ========== -->
      <div class="right-panel">
        <!-- 付款详情 -->
        <div class="side-card payment-card">
          <div class="side-card-title">付款详情</div>
          <div class="payment-rows">
            <div class="payment-row">
              <span class="payment-label">商品总额</span>
              <span class="payment-value">￥{{ itemTotal.toFixed(2) }}</span>
            </div>
            <div class="payment-row">
              <span class="payment-label">运费</span>
              <span class="payment-value">￥{{ (order.freightAmount || 0).toFixed(2) }}</span>
            </div>
            <div class="payment-row" v-if="order.discountAmount">
              <span class="payment-label">优惠</span>
              <span class="payment-value discount">-￥{{ (order.discountAmount || 0).toFixed(2) }}</span>
            </div>
          </div>
          <div class="payment-total">
            <span class="total-label">实付款</span>
            <span class="total-value">￥{{ (order.payAmount || 0).toFixed(2) }}</span>
          </div>
        </div>

        <!-- 订单信息 -->
        <div class="side-card info-card">
          <div class="side-card-title">订单信息</div>
          <div class="info-rows">
            <div class="info-row-item">
              <span class="info-key">订单编号</span>
              <span class="info-val mono">{{ order.orderSn }}</span>
            </div>
            <div class="info-row-item">
              <span class="info-key">创建时间</span>
              <span class="info-val">{{ formatDateTime(order.createdAt) }}</span>
            </div>
            <div class="info-row-item" v-if="(order as any).paymentTime">
              <span class="info-key">付款时间</span>
              <span class="info-val">{{ formatDateTime((order as any).paymentTime) }}</span>
            </div>
            <div class="info-row-item" v-if="order.deliveryTime">
              <span class="info-key">发货时间</span>
              <span class="info-val">{{ formatDateTime(order.deliveryTime) }}</span>
            </div>
            <div class="info-row-item" v-if="(order as any).receiveTime">
              <span class="info-key">收货时间</span>
              <span class="info-val">{{ formatDateTime((order as any).receiveTime) }}</span>
            </div>
          </div>
        </div>

        <!-- 收货信息 -->
        <div class="side-card info-card">
          <div class="side-card-title">收货信息</div>
          <div class="info-rows">
            <div class="info-row-item">
              <span class="info-key">收货人</span>
              <span class="info-val">{{ order.receiverName }}</span>
            </div>
            <div class="info-row-item">
              <span class="info-key">联系电话</span>
              <span class="info-val">{{ order.receiverPhone }}</span>
            </div>
            <div class="info-row-item">
              <span class="info-key">收货地址</span>
              <span class="info-val">{{ order.receiverDetailAddress }}</span>
            </div>
          </div>
        </div>

        <!-- 操作日志 -->
        <div class="side-card info-card" v-if="order.historyList?.length">
          <div class="side-card-title">操作日志</div>
          <div class="log-list">
            <div class="log-item" v-for="log in order.historyList.slice(0, 8)" :key="log.id">
              <div class="log-dot"></div>
              <div class="log-content">
                <div class="log-note">{{ log.note || '--' }}</div>
                <div class="log-meta">
                  <span>{{ log.operateMan }}</span>
                  <span style="margin: 0 6px">·</span>
                  <span>{{ formatDateTime(log.createdAt) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="empty-state">
      <el-empty description="订单不存在" />
    </div>

    <!-- 发货弹窗 -->
    <el-dialog v-model="deliveryVisible" title="订单发货" width="460px" destroy-on-close>
      <el-form :model="deliveryForm" label-width="90px">
        <el-form-item label="物流公司">
          <el-select v-model="deliveryForm.deliveryCompany" placeholder="请选择物流公司" style="width:100%">
            <el-option label="顺丰速运" value="顺丰速运" />
            <el-option label="中通快递" value="中通快递" />
            <el-option label="圆通速递" value="圆通速递" />
            <el-option label="申通快递" value="申通快递" />
            <el-option label="韵达快递" value="韵达快递" />
            <el-option label="京东物流" value="京东物流" />
            <el-option label="EMS" value="EMS" />
          </el-select>
        </el-form-item>
        <el-form-item label="物流单号">
          <el-input v-model="deliveryForm.deliverySn" placeholder="请输入物流单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deliveryVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDelivery">确认发货</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ============================================================
   Global
   ============================================================ */
.order-detail {
  padding: 20px 24px;
  background: #f5f6f7;
  min-height: 100vh;
}

/* ============================================================
   Top bar
   ============================================================ */
.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.back-btn {
  font-size: 14px;
  color: #606266;
}
.order-sn-header {
  font-size: 14px;
  color: #303133;
}
.sn-label {
  font-weight: 500;
}

/* ============================================================
   Main layout — left 2/3 : right 1/3
   ============================================================ */
.main-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.left-panel {
  flex: 2;
  min-width: 0;
}
.right-panel {
  flex: 1;
  min-width: 320px;
  max-width: 420px;
}

/* ============================================================
   Steps card
   ============================================================ */
.steps-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
}
.steps-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.steps-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.steps-wrapper {
  padding: 0 8px;
}

/* closed / refunded banner in steps card */
.closed-banner, .refunded-banner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
}
.closed-text, .refunded-text {
  font-size: 20px;
  font-weight: 600;
  color: #909399;
}

/* ============================================================
   Status banner
   ============================================================ */
.status-banner {
  background: #fff;
  border-left: 4px solid #e75a1c;
  border-radius: 8px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
  border-left-width: 4px;
}
.banner-icon {
  flex-shrink: 0;
}
.banner-text {
  flex: 1;
}
.banner-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}
.banner-sub {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.banner-extra {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  color: #f59e0b;
  font-size: 13px;
}

/* ============================================================
   Logistics info row
   ============================================================ */
.info-row {
  background: #fff;
  border-radius: 8px;
  padding: 14px 24px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #e8e8e8;
}
.info-row-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.info-row-text {
  display: flex;
  flex-direction: column;
}
.info-row-right {
  text-align: right;
}
.info-label {
  font-size: 12px;
  color: #909399;
}
.info-value {
  font-size: 14px;
  color: #303133;
}
.mono {
  font-family: 'SF Mono', 'Menlo', monospace;
  letter-spacing: 0.5px;
}

/* ============================================================
   Shop bar
   ============================================================ */
.shop-bar {
  background: #fff;
  border-radius: 8px 8px 0 0;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e8e8e8;
  border-bottom: none;
}
.shop-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e75a1c;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.shop-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* ============================================================
   Product list
   ============================================================ */
.product-list {
  background: #fff;
  border-radius: 0 0 8px 8px;
  border: 1px solid #e8e8e8;
  border-top: none;
  margin-bottom: 12px;
}
.product-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}
.product-row:last-child {
  border-bottom: none;
}
.product-image {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
}
.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.product-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
}
.product-info {
  flex: 1;
  min-width: 0;
}
.product-name {
  font-size: 14px;
  color: #303133;
  text-decoration: none;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}
.product-name:hover {
  color: #e75a1c;
}
.product-spec {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.product-price {
  font-size: 14px;
  color: #303133;
  min-width: 70px;
  text-align: center;
}
.product-quantity {
  font-size: 14px;
  color: #606266;
  min-width: 50px;
  text-align: center;
}
.product-subtotal {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  min-width: 80px;
  text-align: right;
}

/* ============================================================
   Action bar
   ============================================================ */
.action-bar {
  background: #fff;
  border-radius: 8px;
  padding: 16px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border: 1px solid #e8e8e8;
  margin-bottom: 12px;
}

/* ============================================================
   Right side cards
   ============================================================ */
.side-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
}
.side-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

/* Payment card */
.payment-rows {
  margin-bottom: 12px;
}
.payment-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}
.payment-label {
  font-size: 13px;
  color: #606266;
}
.payment-value {
  font-size: 14px;
  color: #303133;
}
.payment-value.discount {
  color: #22c55e;
}
.payment-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.total-label {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
.total-value {
  font-size: 22px;
  font-weight: 700;
  color: #e75a1c;
}

/* Info card */
.info-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.info-row-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.info-key {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
  min-width: 56px;
}
.info-val {
  font-size: 13px;
  color: #303133;
  text-align: right;
  word-break: break-all;
}

/* Log list */
.log-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.log-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #fafafa;
}
.log-item:last-child {
  border-bottom: none;
}
.log-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  margin-top: 5px;
  flex-shrink: 0;
}
.log-content {
  flex: 1;
  min-width: 0;
}
.log-note {
  font-size: 13px;
  color: #303133;
  line-height: 1.4;
}
.log-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* ============================================================
   Responsive
   ============================================================ */
@media (max-width: 1024px) {
  .main-layout {
    flex-direction: column;
  }
  .right-panel {
    max-width: none;
    min-width: 0;
  }
}
</style>
