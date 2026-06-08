<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import LogisticsDialog from './components/logisticsDialog.vue'
import { formatDateTime } from '@/utils/datetime'
import type { OmsOrder } from '@/types/order'
import { getOrderListAPI, orderUpdateCloseAPI, orderDeleteByIdsAPI } from '@/apis/order'

const router = useRouter()

const listQuery = ref({
  orderSn: '',
  receiverKeyword: '',
  createTime: '',
  status: undefined as number | undefined,
  orderType: undefined as number | undefined,
  sourceType: undefined as number | undefined,
  pageNum: 1,
  pageSize: 10,
})

const list = ref<OmsOrder[]>([])
const total = ref(0)
const listLoading = ref(false)
const multipleSelection = ref<OmsOrder[]>([])
const operateType = ref<number>()
const logisticsDialogVisible = ref(false)

const closeOrderData = ref({
  dialogVisible: false,
  content: '',
  orderIds: [] as number[],
})

const statusOptions = [
  { label: '待付款', value: 0 },
  { label: '待发货', value: 1 },
  { label: '已发货', value: 2 },
  { label: '已完成', value: 3 },
  { label: '已关闭', value: 4 },
]

const orderTypeOptions = [
  { label: '正常订单', value: 0 },
  { label: '秒杀订单', value: 1 },
]

const sourceTypeOptions = [
  { label: 'PC订单', value: 0 },
  { label: 'APP订单', value: 1 },
]

const operateOptions = [
  { label: '批量发货', value: 1 },
  { label: '关闭订单', value: 2 },
  { label: '删除订单', value: 3 },
]

const formatPayType = (value?: number) => {
  if (value === 1) return '支付宝'
  if (value === 2) return '微信'
  return '未支付'
}

const formatSourceType = (value?: number) => {
  return value === 1 ? 'APP订单' : 'PC订单'
}

const formatStatus = (value?: number) => {
  if (value === 1) return '待发货'
  if (value === 2) return '已发货'
  if (value === 3) return '已完成'
  if (value === 4) return '已关闭'
  return '待付款'
}

async function fetchData() {
  listLoading.value = true
  try {
    const res = await getOrderListAPI(listQuery.value)
    list.value = res.list
    total.value = res.total
  } finally {
    listLoading.value = false
  }
}

onMounted(() => { fetchData() })

const handleResetSearch = () => {
  listQuery.value = { orderSn: '', receiverKeyword: '', createTime: '', status: undefined, orderType: undefined, sourceType: undefined, pageNum: 1, pageSize: 10 }
  fetchData()
}

const handleSearchList = () => {
  listQuery.value.pageNum = 1
  fetchData()
}

const handleSelectionChange = (val: OmsOrder[]) => { multipleSelection.value = val }

const handleViewOrder = (_index: number, row: OmsOrder) => {
  router.push({ path: '/oms/orderDetail', query: { id: row.id } })
}

const handleCloseOrder = (_index: number, row: OmsOrder) => {
  closeOrderData.value.dialogVisible = true
  closeOrderData.value.orderIds = [row.id!]
}

const handleDeliveryOrder = (_index: number, row: OmsOrder) => {
  console.log('订单发货', row)
}

const handleViewLogistics = (_index: number, _row: OmsOrder) => {
  logisticsDialogVisible.value = true
}

const handleDeleteOrder = async (_index: number, row: OmsOrder) => {
  await ElMessageBox.confirm('是否要进行该删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  await orderDeleteByIdsAPI({ ids: String(row.id) })
  fetchData()
  ElMessage({ message: '删除成功！', type: 'success', duration: 1000 })
}

const handleBatchOperate = async () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) {
    ElMessage({ message: '请选择要操作的订单', type: 'warning', duration: 1000 })
    return
  }
  if (operateType.value === 2) {
    const ids = multipleSelection.value.filter(item => item.status === 0).map(item => item.id!)
    if (ids.length === 0) { ElMessage({ message: '选中订单中没有可关闭的订单', type: 'warning', duration: 1000 }); return }
    closeOrderData.value.orderIds = ids
    closeOrderData.value.dialogVisible = true
  } else if (operateType.value === 3) {
    const ids = multipleSelection.value.filter(item => item.status === 4).map(item => item.id!)
    if (ids.length === 0) { ElMessage({ message: '只能删除已关闭的订单', type: 'warning', duration: 1000 }); return }
    await deleteOrderFn(ids)
  } else if (operateType.value === 1) {
    const items = multipleSelection.value.filter(item => item.status === 1)
    if (!items || items.length < 1) { ElMessage({ message: '选中订单中没有可以发货的订单', type: 'warning', duration: 1000 }); return }
    console.log('批量发货', items)
  }
}

const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; fetchData() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; fetchData() }

const handleCloseOrderConfirm = async () => {
  if (!closeOrderData.value.content) { ElMessage({ message: '操作备注不能为空', type: 'warning', duration: 1000 }); return }
  await orderUpdateCloseAPI({ ids: closeOrderData.value.orderIds.join(','), note: closeOrderData.value.content })
  closeOrderData.value.dialogVisible = false
  closeOrderData.value.content = ''
  fetchData()
  ElMessage({ message: '关闭成功', type: 'success', duration: 1000 })
}

const deleteOrderFn = async (ids: number[]) => {
  await ElMessageBox.confirm('是否要进行该删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  await orderDeleteByIdsAPI({ ids: ids.join(',') })
  fetchData()
  ElMessage({ message: '删除成功！', type: 'success', duration: 1000 })
}
</script>

<template>
  <div class="app-container">
    <el-card class="filter-container" shadow="never">
      <div>
        <el-icon class="el-icon-middle"><Search /></el-icon>
        <span>筛选搜索</span>
        <el-button style="float: right" type="primary" @click="handleSearchList">查询搜索</el-button>
        <el-button style="float: right; margin-right: 15px" @click="handleResetSearch">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="输入搜索：">
            <el-input v-model="listQuery.orderSn" class="input-width" placeholder="订单编号" />
          </el-form-item>
          <el-form-item label="收货人：">
            <el-input v-model="listQuery.receiverKeyword" class="input-width" placeholder="收货人姓名/手机号码" />
          </el-form-item>
          <el-form-item label="提交时间：">
            <el-date-picker class="input-width" v-model="listQuery.createTime" value-format="YYYY-MM-DD" type="date" placeholder="请选择时间" />
          </el-form-item>
          <el-form-item label="订单状态：">
            <el-select v-model="listQuery.status" class="input-width" placeholder="全部" clearable>
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="订单分类：">
            <el-select v-model="listQuery.orderType" class="input-width" placeholder="全部" clearable>
              <el-option v-for="item in orderTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="订单来源：">
            <el-select v-model="listQuery.sourceType" class="input-width" placeholder="全部" clearable>
              <el-option v-for="item in sourceTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
    </el-card>

    <div class="table-container">
      <el-table ref="orderTable" :data="list" style="width: 100%" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center" />
        <el-table-column label="编号" width="80" align="center">
          <template #default="scope">{{ scope.row.id }}</template>
        </el-table-column>
        <el-table-column label="订单编号" width="180" align="center">
          <template #default="scope">{{ scope.row.orderSn }}</template>
        </el-table-column>
        <el-table-column label="提交时间" width="180" align="center">
          <template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template>
        </el-table-column>
        <el-table-column label="用户账号" align="center">
          <template #default="scope">{{ scope.row.memberUsername }}</template>
        </el-table-column>
        <el-table-column label="订单金额" width="120" align="center">
          <template #default="scope">￥{{ scope.row.totalAmount?.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="支付方式" width="120" align="center">
          <template #default="scope">{{ formatPayType(scope.row.payType) }}</template>
        </el-table-column>
        <el-table-column label="订单来源" width="120" align="center">
          <template #default="scope">{{ formatSourceType(scope.row.sourceType) }}</template>
        </el-table-column>
        <el-table-column label="订单状态" width="120" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 0 ? 'warning' : scope.row.status === 1 ? 'primary' : scope.row.status === 2 ? 'success' : scope.row.status === 3 ? '' : 'info'" size="small">
              {{ formatStatus(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="scope">
            <el-button size="small" @click="handleViewOrder(scope.$index, scope.row)">查看订单</el-button>
            <el-button size="small" @click="handleCloseOrder(scope.$index, scope.row)" v-show="scope.row.status === 0">关闭订单</el-button>
            <el-button size="small" @click="handleDeliveryOrder(scope.$index, scope.row)" v-show="scope.row.status === 1">订单发货</el-button>
            <el-button size="small" @click="handleViewLogistics(scope.$index, scope.row)" v-show="scope.row.status === 2 || scope.row.status === 3">订单跟踪</el-button>
            <el-button size="small" type="danger" @click="handleDeleteOrder(scope.$index, scope.row)" v-show="scope.row.status === 4">删除订单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="batch-operate-container">
      <el-select v-model="operateType" placeholder="批量操作">
        <el-option v-for="item in operateOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button style="margin-left: 20px" @click="handleBatchOperate" type="primary">确定</el-button>
    </div>

    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes, prev, pager, next, jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>

    <!-- 关闭订单弹窗 -->
    <el-dialog title="关闭订单" v-model="closeOrderData.dialogVisible" width="30%">
      <span style="vertical-align: top">操作备注：</span>
      <el-input style="width: 80%" type="textarea" :rows="5" placeholder="请输入内容" v-model="closeOrderData.content" />
      <template #footer>
        <el-button @click="closeOrderData.dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleCloseOrderConfirm">确 定</el-button>
      </template>
    </el-dialog>

    <LogisticsDialog v-model="logisticsDialogVisible" />
  </div>
</template>

<style scoped>
.input-width { width: 203px; }
.batch-operate-container { display: inline-block; margin-top: 12px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
