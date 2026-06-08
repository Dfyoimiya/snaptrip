<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'

const route = useRoute()
const router = useRouter()
const orderId = ref(route.query.id as string || '')

const loading = ref(true)
const order = ref<any>(null)

// 模拟订单详情数据
const orderDataMap: Record<string, any> = {
  '1': {
    id: 1, orderSn: 'ORD202506010001', createTime: '2025-06-01 10:23:15',
    memberUsername: 'zhangsan', receiverName: '张三', receiverPhone: '13800138001',
    receiverDetailAddress: '北京市朝阳区建国路88号', totalAmount: 8999.00, freightAmount: 0.00,
    discountAmount: 500.00, payAmount: 8499.00, payType: 1, sourceType: 0,
    status: 2, deliveryCompany: '顺丰速运', deliverySn: 'SF1234567890',
    autoConfirmDay: 7, remark: '请尽快发货', deleteStatus: 0,
    items: [
      { id: 1, productId: 1, productName: 'iPhone 15 Pro', productPic: '', productPrice: 8999, productQuantity: 1, productAttr: '256GB 黑色' },
    ]
  },
  '2': {
    id: 2, orderSn: 'ORD202506010002', createTime: '2025-06-01 11:05:30',
    memberUsername: 'lisi', receiverName: '李四', receiverPhone: '13800138002',
    receiverDetailAddress: '上海市浦东新区陆家嘴环路1000号', totalAmount: 12597.00, freightAmount: 15.00,
    discountAmount: 1000.00, payAmount: 11612.00, payType: 2, sourceType: 1,
    status: 1, deliveryCompany: '', deliverySn: '',
    autoConfirmDay: 7, remark: '', deleteStatus: 0,
    items: [
      { id: 2, productId: 2, productName: '华为Mate60 Pro', productPic: '', productPrice: 6999, productQuantity: 1, productAttr: '12+512GB 雅丹黑' },
      { id: 3, productId: 3, productName: 'AirPods Pro 2', productPic: '', productPrice: 1599, productQuantity: 1, productAttr: '白色' },
    ]
  },
}

const statusMap: Record<number, { label: string; type: string }> = {
  0: { label: '待付款', type: 'warning' },
  1: { label: '待发货', type: 'primary' },
  2: { label: '已发货', type: 'success' },
  3: { label: '已完成', type: 'info' },
  4: { label: '已关闭', type: 'danger' },
  5: { label: '退款中', type: 'warning' },
}

const payTypeMap: Record<number, string> = {
  0: '未支付', 1: '支付宝', 2: '微信支付', 3: '银行卡',
}

function loadOrder() {
  loading.value = true
  setTimeout(() => {
    order.value = orderDataMap[orderId.value] || {
      id: Number(orderId.value), orderSn: `ORD20250601${String(orderId.value).padStart(4, '0')}`,
      createTime: '2025-06-01 12:00:00',
      memberUsername: 'unknown', receiverName: '未知用户', receiverPhone: '--',
      receiverDetailAddress: '--', totalAmount: 0, freightAmount: 0,
      discountAmount: 0, payAmount: 0, payType: 0, sourceType: 0,
      status: 0, deliveryCompany: '', deliverySn: '',
      autoConfirmDay: 7, remark: '', deleteStatus: 0, items: [],
    }
    loading.value = false
  }, 300)
}

function handleBack() {
  router.back()
}

onMounted(() => {
  if (!orderId.value) {
    ElMessage.error('订单ID不能为空')
    router.push('/oms/order')
    return
  }
  loadOrder()
})
</script>

<template>
  <div class="app-container">
    <!-- 顶部操作栏 -->
    <div style="margin-bottom: 16px">
      <el-button @click="handleBack">
        <el-icon><ArrowLeft /></el-icon>返回列表
      </el-button>
    </div>

    <el-row v-loading="loading" :gutter="16">
      <!-- 订单基本信息 -->
      <el-col :span="24">
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div class="card-header">
              <span>订单信息</span>
              <el-tag :type="statusMap[order?.status]?.type || 'info'" size="large">
                {{ statusMap[order?.status]?.label || '未知' }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="订单编号">{{ order?.orderSn }}</el-descriptions-item>
            <el-descriptions-item label="下单时间">{{ order?.createTime }}</el-descriptions-item>
            <el-descriptions-item label="支付方式">{{ payTypeMap[order?.payType] || '--' }}</el-descriptions-item>
            <el-descriptions-item label="订单来源">
              {{ order?.sourceType === 0 ? 'PC端' : order?.sourceType === 1 ? 'APP端' : '小程序' }}
            </el-descriptions-item>
            <el-descriptions-item label="自动确认天数">{{ order?.autoConfirmDay }}天</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ order?.remark || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 收货人信息 -->
      <el-col :span="12">
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div class="card-header">
              <span>收货人信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="会员帐号">{{ order?.memberUsername }}</el-descriptions-item>
            <el-descriptions-item label="收货人">{{ order?.receiverName }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ order?.receiverPhone }}</el-descriptions-item>
            <el-descriptions-item label="收货地址">{{ order?.receiverDetailAddress }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 物流信息 -->
      <el-col :span="12">
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div class="card-header">
              <span>物流信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="物流公司">{{ order?.deliveryCompany || '--' }}</el-descriptions-item>
            <el-descriptions-item label="物流单号">{{ order?.deliverySn || '--' }}</el-descriptions-item>
            <el-descriptions-item label="发货状态">
              <el-tag v-if="order?.status >= 2" type="success">已发货</el-tag>
              <el-tag v-else-if="order?.status === 1" type="primary">待发货</el-tag>
              <el-tag v-else type="info">未发货</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 商品信息 -->
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>商品信息</span>
            </div>
          </template>
          <el-table :data="order?.items || []" border style="width: 100%">
            <el-table-column label="商品图片" width="100" align="center">
              <template #default>
                <div style="width: 60px; height: 60px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center">
                  <el-icon :size="24" style="color: #909399"><Picture /></el-icon>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="商品名称" prop="productName" min-width="180" />
            <el-table-column label="商品属性" prop="productAttr" width="160" />
            <el-table-column label="单价" prop="productPrice" width="100" align="center">
              <template #default="{ row }">
                <span>￥{{ row.productPrice }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数量" prop="productQuantity" width="80" align="center" />
            <el-table-column label="小计" width="100" align="center">
              <template #default="{ row }">
                <span style="color: #f56c6c; font-weight: bold">￥{{ row.productPrice * row.productQuantity }}</span>
              </template>
            </el-table-column>
          </el-table>

          <!-- 金额汇总 -->
          <div style="margin-top: 16px; text-align: right">
            <div style="margin-bottom: 4px">
              <span style="color: #606266">商品总额：</span>
              <span>￥{{ order?.totalAmount?.toFixed(2) }}</span>
            </div>
            <div style="margin-bottom: 4px">
              <span style="color: #606266">运费：</span>
              <span>￥{{ order?.freightAmount?.toFixed(2) }}</span>
            </div>
            <div style="margin-bottom: 4px">
              <span style="color: #606266">优惠金额：</span>
              <span style="color: #67c23a">-￥{{ order?.discountAmount?.toFixed(2) }}</span>
            </div>
            <div style="font-size: 18px; font-weight: bold; margin-top: 8px">
              <span style="color: #606266">实付金额：</span>
              <span style="color: #f56c6c">￥{{ order?.payAmount?.toFixed(2) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.app-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
