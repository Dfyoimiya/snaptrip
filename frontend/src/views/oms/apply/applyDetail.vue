<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'

const route = useRoute()
const router = useRouter()

const defaultUpdateStatusParam = {
  id: 0, companyAddressId: 0, handleMan: 'admin', handleNote: '',
  receiveMan: 'admin', receiveNote: '', returnAmount: 0, status: 0
}

const id = ref<number>()
const orderReturnApply = ref<any>({})
const proofPics = ref<string[]>([])
const productList = ref<any[]>([])
const companyAddressList = ref<any[]>([])
const updateStatusParam = ref(Object.assign({}, defaultUpdateStatusParam))

const allMockData: Record<number, any> = {
  1: { id: 1, orderId: 101, productId: 1, orderSn: 'ORD-20240528001', createTime: '2024-05-28T10:30:00', memberUsername: 'user_001', returnAmount: 9999, returnName: '张三', returnPhone: '13800138001', status: 0, reason: '商品质量问题', description: '收到的手机屏幕有划痕', productPic: 'https://picsum.photos/seed/iphone/200/200', productName: 'iPhone 15 Pro Max', productBrand: 'Apple', productAttr: '[{\"key\":\"颜色\",\"value\":\"黑色\"},{\"key\":\"容量\",\"value\":\"256GB\"}]', productCount: 1, productRealPrice: 9999, proofPics: 'https://picsum.photos/seed/p1/200/200,https://picsum.photos/seed/p2/200/200' },
  2: { id: 2, orderId: 102, productId: 2, orderSn: 'ORD-20240527002', createTime: '2024-05-27T14:20:00', memberUsername: 'user_002', returnAmount: 6999, returnName: '李四', returnPhone: '13800138002', status: 1, reason: '商品与描述不符', description: '颜色与图片不符', productPic: 'https://picsum.photos/seed/huawei/200/200', productName: '华为 Mate 60 Pro', productBrand: '华为', productAttr: '[{\"key\":\"颜色\",\"value\":\"白色\"},{\"key\":\"容量\",\"value\":\"256GB\"}]', productCount: 1, productRealPrice: 6999, proofPics: 'https://picsum.photos/seed/p3/200/200' },
  3: { id: 3, orderId: 103, productId: 3, orderSn: 'ORD-20240526003', createTime: '2024-05-26T09:10:00', memberUsername: 'user_003', returnAmount: 3798, returnName: '王五', returnPhone: '13800138003', status: 2, reason: '不想要了', description: '买多了想退', productPic: 'https://picsum.photos/seed/airpods/200/200', productName: 'AirPods Pro 2', productBrand: 'Apple', productAttr: '[{\"key\":\"颜色\",\"value\":\"白色\"}]', productCount: 2, productRealPrice: 1899, proofPics: '', handleMan: 'admin', handleTime: '2024-05-27T10:00:00', handleNote: '同意退货', receiveMan: 'admin', receiveTime: '2024-05-29T14:00:00', receiveNote: '商品已验收' },
  4: { id: 4, orderId: 104, productId: 4, orderSn: 'ORD-20240525004', createTime: '2024-05-25T16:45:00', memberUsername: 'user_004', returnAmount: 5999, returnName: '赵六', returnPhone: '13800138004', status: 3, reason: '其他原因', description: '价格降了', productPic: 'https://picsum.photos/seed/mi14/200/200', productName: '小米14 Ultra', productBrand: '小米', productAttr: '[{\"key\":\"颜色\",\"value\":\"黑色\"},{\"key\":\"容量\",\"value\":\"512GB\"}]', productCount: 1, productRealPrice: 5999, proofPics: '' },
}

const getDetail = () => {
  const data = allMockData[id.value || 1]
  if (data) {
    orderReturnApply.value = data
    productList.value = [data]
    if (data.proofPics) proofPics.value = data.proofPics.split(',')
    if (data.status === 1 || data.status === 2) {
      updateStatusParam.value.returnAmount = data.returnAmount
      updateStatusParam.value.companyAddressId = data.companyAddressId || 1
    }
  }
}

onMounted(() => {
  id.value = Number(route.query.id) || 1
  getDetail()
})

const totalAmount = computed(() => {
  if (orderReturnApply.value) return (orderReturnApply.value.productRealPrice || 0) * (orderReturnApply.value.productCount || 0)
  return 0
})

const currentAddress = computed(() => {
  const idValue = updateStatusParam.value.companyAddressId
  if (!companyAddressList.value) return undefined
  return companyAddressList.value.find((item: any) => item.id === idValue)
})

const formatStatus = (status?: number) => {
  if (status === 1) return '退货中'
  if (status === 2) return '已完成'
  if (status === 3) return '已拒绝'
  return '待处理'
}

const formatRegion = (address?: any) => {
  if (!address) return ''
  let str = address.province || ''
  if (address.city) str += '  ' + address.city
  str += '  ' + (address.region || '')
  return str
}

const handleViewOrder = () => { router.push({ path: '/oms/orderDetail', query: { id: orderReturnApply.value.orderId } }) }

const handleUpdateStatus = async (status: number) => {
  updateStatusParam.value.status = status
  await ElMessageBox.confirm('是否要进行此操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  orderReturnApply.value.status = status
  if (status === 1) { orderReturnApply.value.handleMan = 'admin'; orderReturnApply.value.handleTime = new Date().toISOString(); orderReturnApply.value.handleNote = updateStatusParam.value.handleNote }
  if (status === 2) { orderReturnApply.value.receiveMan = 'admin'; orderReturnApply.value.receiveTime = new Date().toISOString(); orderReturnApply.value.receiveNote = updateStatusParam.value.receiveNote }
  ElMessage({ type: 'success', message: '操作成功!', duration: 1000 })
  router.back()
}
</script>

<template>
  <div class="detail-container">
    <el-card shadow="never">
      <span class="font-title-medium">退货商品</span>
      <el-table border class="standard-margin" ref="productTable" :data="productList">
        <el-table-column label="商品图片" width="160" align="center">
          <template #default="scope"><img style="height:80px" :src="scope.row.productPic"></template>
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
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.createTime) }}</el-col>
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
            ￥<el-input size="small" v-model="updateStatusParam.returnAmount" :disabled="orderReturnApply.status !== 0" style="width:200px;margin-left: 10px"></el-input>
          </el-col>
        </el-row>
      </div>
      <div class="form-container-border" v-show="orderReturnApply.status !== 0">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">处理人员</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.handleMan }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">处理时间</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.handleTime) }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">处理备注</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.handleNote }}</el-col>
        </el-row>
      </div>
      <div class="form-container-border" v-show="orderReturnApply.status === 2">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">收货人员</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.receiveMan }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">收货时间</el-col>
          <el-col class="form-border font-small" :span="18">{{ formatDateTime(orderReturnApply.receiveTime) }}</el-col>
        </el-row>
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6">收货备注</el-col>
          <el-col class="form-border font-small" :span="18">{{ orderReturnApply.receiveNote }}</el-col>
        </el-row>
      </div>
      <div class="form-container-border" v-show="orderReturnApply.status === 0">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:52px;line-height:32px">处理备注</el-col>
          <el-col class="form-border font-small" :span="18">
            <el-input size="small" v-model="updateStatusParam.handleNote" style="width:200px;margin-left: 10px"></el-input>
          </el-col>
        </el-row>
      </div>
      <div class="form-container-border" v-show="orderReturnApply.status === 1">
        <el-row>
          <el-col class="form-border form-left-bg font-small" :span="6" style="height:52px;line-height:32px">收货备注</el-col>
          <el-col class="form-border font-small" :span="18">
            <el-input size="small" v-model="updateStatusParam.receiveNote" style="width:200px;margin-left: 10px"></el-input>
          </el-col>
        </el-row>
      </div>
      <div style="margin-top:15px;text-align: center" v-show="orderReturnApply.status === 0">
        <el-button type="primary" size="small" @click="handleUpdateStatus(1)">确认退货</el-button>
        <el-button type="danger" size="small" @click="handleUpdateStatus(3)">拒绝退货</el-button>
      </div>
      <div style="margin-top:15px;text-align: center" v-show="orderReturnApply.status === 1">
        <el-button type="primary" size="small" @click="handleUpdateStatus(2)">确认收货</el-button>
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
