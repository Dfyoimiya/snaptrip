<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'
import { getOrderDetailByIdAPI } from '@/apis/order'

const route = useRoute()
const router = useRouter()
const orderId = ref('')

const loading = ref(true)
const order = ref<any>(null)

const statusMap: Record<number, { label: string; type: 'primary' | 'success' | 'warning' | 'info' | 'danger' }> = {
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

async function loadOrder() {
  loading.value = true
  try {
    const res = await getOrderDetailByIdAPI(orderId.value)
    const detail = (res as any).data || res
    // 映射 API 字段 → 模板兼容字段
    order.value = {
      ...detail,
      items: detail.orderItemList || detail.items || [],
      memberUsername: detail.memberUsername || detail.memberName || '',
      receiverDetailAddress: detail.receiverDetailAddress || detail.receiverAddress || '',
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
            <el-descriptions-item label="下单时间">{{ order?.createdAt }}</el-descriptions-item>
            <el-descriptions-item label="支付方式">{{ payTypeMap[order?.payType] || '--' }}</el-descriptions-item>
            <el-descriptions-item label="订单来源">
              {{ order?.sourceType === 0 ? '电脑端' : order?.sourceType === 1 ? '移动应用端' : '小程序' }}
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
            <el-table-column label="商品属性" prop="spec" width="160" />
            <el-table-column label="单价" prop="price" width="100" align="center">
              <template #default="{ row }">
                <span>￥{{ row.price }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数量" prop="quantity" width="80" align="center" />
            <el-table-column label="小计" width="100" align="center">
              <template #default="{ row }">
                <span style="color: #f56c6c; font-weight: bold">￥{{ row.price * row.quantity }}</span>
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
