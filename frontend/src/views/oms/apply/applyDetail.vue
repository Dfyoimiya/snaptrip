<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'
import { getReturnApplyDetailAPI, updateReturnApplyStatusAPI } from '@/apis/returnApply'
import type { OmsOrderReturnApply } from '@/types/returnApply'

const route = useRoute()
const router = useRouter()

const id = ref('')
const orderReturnApply = ref<OmsOrderReturnApply>({})
const proofPics = ref<string[]>([])
const detailLoading = ref(false)

const updateStatusParam = ref({
  return_amount: 0,
  handle_note: '',
  receive_note: '',
})

// 状态: 0=待处理 1=退货中 2=已拒绝 3=已退款
const formatStatus = (status?: number) => {
  const map: Record<number, string> = { 0: '待处理', 1: '退货中', 2: '已拒绝', 3: '已退款' }
  return map[status ?? 0] || ''
}

const totalAmount = computed(() => {
  return (orderReturnApply.value.productRealPrice || 0) * (orderReturnApply.value.productCount || 0)
})

const fetchDetail = async () => {
  detailLoading.value = true
  try {
    const res = await getReturnApplyDetailAPI(id.value)
    orderReturnApply.value = res.data
    if (res.data.proofPics) {
      proofPics.value = res.data.proofPics.split(',')
    }
    if (res.data.returnAmount !== undefined) {
      updateStatusParam.value.return_amount = res.data.returnAmount
    }
  } catch {
    ElMessage.error('获取退货申请详情失败')
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  id.value = (route.query.id as string) || ''
  if (!id.value) {
    ElMessage.error('缺少退货申请ID')
    router.back()
    return
  }
  fetchDetail()
})

const handleViewOrder = () => {
  if (!orderReturnApply.value.orderId) return ElMessage.error('订单ID不能为空')
  router.push({ path: '/oms/orderDetail', query: { id: orderReturnApply.value.orderId } })
}

const handleUpdateStatus = async (status: number) => {
  const confirmMessages: Record<number, string> = {
    1: '确认将该申请标记为"退货中"？',
    2: '确认拒绝该退货申请？',
    3: '确认退款？该操作将把订单状态改为"已退款"。',
  }
  try {
    await ElMessageBox.confirm(
      confirmMessages[status] || '是否要进行此操作?',
      '提示',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
    await updateReturnApplyStatusAPI(id.value, {
      status,
      handle_note: updateStatusParam.value.handle_note || undefined,
      receive_note: updateStatusParam.value.receive_note || undefined,
      return_amount: updateStatusParam.value.return_amount || undefined,
    })
    ElMessage({ type: 'success', message: '操作成功!', duration: 1000 })
    router.back()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage({ type: 'error', message: '操作失败' })
    }
  }
}
</script>

<template>
  <div class="detail-container" v-loading="detailLoading">
    <el-card shadow="never">
      <span class="font-title-medium">退货商品</span>
      <el-table border class="standard-margin" :data="orderReturnApply ? [orderReturnApply] : []">
        <el-table-column label="商品图片" width="160" align="center">
          <template #default="scope">
            <img style="height:80px" :src="scope.row.productPic" v-if="scope.row.productPic">
          </template>
        </el-table-column>
        <el-table-column label="商品名称" align="center">
          <template #default="scope">
            <span class="font-small">{{ scope.row.productName }}</span><br>
            <span class="font-small">品牌：{{ scope.row.productBrand }}</span>
          </template>
        </el-table-column>
        <el-table-column label="价格/货号" width="180" align="center">
          <template #default="scope">
            <span class="font-small">价格：￥{{ scope.row.productRealPrice }}</span><br>
            <span class="font-small">货号：NO.{{ scope.row.productId }}</span>
          </template>
        </el-table-column>
        <el-table-column label="属性" width="180" align="center">
          <template #default="scope">{{ scope.row.productAttr }}</template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="center">
          <template #default="scope">{{ scope.row.productCount }}</template>
        </el-table-column>
        <el-table-column label="小计" width="100" align="center">
          <template>￥{{ totalAmount }}</template>
        </el-table-column>
      </el-table>
      <div style="float:right;margin-top:15px;margin-bottom:15px">
        <span class="font-title-medium">合计：</span>
        <span class="font-title-medium color-danger">￥{{ totalAmount }}</span>
      </div>
    </el-card>

    <el-card shadow="never" class="standard-margin">
      <span class="font-title-medium">服务单信息</span>
      <div class="form-container-border">
        <el-row>
          <el-col :span="6" class="form-border form-left-bg font-small">服务单号</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.id }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">申请状态</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatStatus(orderReturnApply.status) }}</el-col>
        </el-row>
        <el-row>
          <el-col :span="6" class="form-border form-left-bg font-small" style="height:50px;line-height:30px">订单编号</el-col>
          <el-col class="form-border font-small" :span="18" style="height:50px">
            {{ orderReturnApply.orderSn }}
            <el-button link type="primary" size="small" @click="handleViewOrder">查看</el-button>
          </el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">申请时间</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.createdAt) }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">用户账号</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.memberUsername }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">联系人</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.returnName }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">联系电话</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.returnPhone }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">退货原因</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.reason }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">问题描述</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.description }}</el-col>
        </el-row>
        <el-row v-if="proofPics.length > 0">
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:100px;line-height:80px">凭证图片</el-col>
          <el-col class="form-border font-small" :span="18" style="height:100px">
            <img v-for="item in proofPics" style="width:80px;height:80px;margin-right:10px" :src="item" :key="item">
          </el-col>
        </el-row>
      </div>

      <div class="form-container-border">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">订单金额</el-col>
          <el-col class="form-border font-small" :span="18">￥{{ totalAmount }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:52px;line-height:32px">确认退款金额</el-col>
          <el-col class="form-border font-small" style="height:52px" :span="18">
            ￥<el-input size="small" v-model="updateStatusParam.return_amount" :disabled="orderReturnApply.status !== 0" style="width:200px;margin-left: 10px"></el-input>
          </el-col>
        </el-row>
      </div>

      <!-- 已处理信息 -->
      <div class="form-container-border" v-show="orderReturnApply.status !== 0">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">处理人员</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.handleMan }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">处理时间</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.handleTime) }}</el-col>
        </el-row>
        <el-row v-if="orderReturnApply.handleNote">
          <el-col class="form-border form-left-bg font-small" :span="6">处理备注</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.handleNote }}</el-col>
        </el-row>
      </div>

      <!-- 收货信息（状态=1 退货中 or 3 已退款） -->
      <div class="form-container-border" v-show="orderReturnApply.status === 1 || orderReturnApply.status === 3">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">收货人员</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.receiveMan }}</el-col>
        </el-row>
        <el-row v-if="orderReturnApply.receiveTime">
          <el-col class="form-border form-left-bg font-small" :span="6">收货时间</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.receiveTime) }}</el-col>
        </el-row>
        <el-row v-if="orderReturnApply.receiveNote">
          <el-col class="form-border form-left-bg font-small" :span="6">收货备注</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.receiveNote }}</el-col>
        </el-row>
      </div>

      <!-- 待处理: 处理备注输入 -->
      <div class="form-container-border" v-show="orderReturnApply.status === 0">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:52px;line-height:32px">处理备注</el-col>
          <el-col class="form-border font-small" :span="18">
            <el-input size="small" v-model="updateStatusParam.handle_note" style="width:200px;margin-left: 10px" placeholder="可选"></el-input>
          </el-col>
        </el-row>
      </div>

      <!-- 退货中: 收货备注输入 -->
      <div class="form-container-border" v-show="orderReturnApply.status === 1">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:52px;line-height:32px">收货备注</el-col>
          <el-col class="form-border font-small" :span="18">
            <el-input size="small" v-model="updateStatusParam.receive_note" style="width:200px;margin-left: 10px" placeholder="可选"></el-input>
          </el-col>
        </el-row>
      </div>

      <!-- 操作按钮: 待处理 → 确认退货 / 拒绝退货 -->
      <div style="margin-top:15px;text-align: center" v-show="orderReturnApply.status === 0">
        <el-button type="primary" size="small" @click="handleUpdateStatus(1)">确认退货</el-button>
        <el-button type="danger" size="small" @click="handleUpdateStatus(2)">拒绝退货</el-button>
      </div>

      <!-- 操作按钮: 退货中 → 确认退款 -->
      <div style="margin-top:15px;text-align: center" v-show="orderReturnApply.status === 1">
        <el-button type="primary" size="small" @click="handleUpdateStatus(3)">确认退款</el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.detail-container { width: 960px; margin: 20px auto; padding: 35px 35px 15px 35px; }
.standard-margin { margin-top: 15px; }
.form-border { border-right: 1px solid #DCDFE6; border-bottom: 1px solid #DCDFE6; padding: 10px; }
.form-container-border { border-left: 1px solid #DCDFE6; border-top: 1px solid #DCDFE6; margin-top: 15px; }
.form-left-bg { background: #F2F6FC; }
.font-title-medium { font-size: 16px; font-weight: 500; }
.font-small { font-size: 14px; }
.color-danger { color: #f56c6c; }
</style>
