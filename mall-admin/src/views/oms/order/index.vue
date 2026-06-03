<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import LogisticsDialog from './components/logisticsDialog.vue'
import { formatDateTime } from '@/utils/datetime'
import type { OmsOrder } from '@/types/order'

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

// 模拟订单数据
const allList = ref<OmsOrder[]>([
  { id: 1, orderSn: 'ORD-20240528001', createTime: '2024-05-28T10:30:00', memberUsername: 'user_001', totalAmount: 9999, payType: 1, sourceType: 0, status: 0, orderType: 0, receiverName: '张三', receiverPhone: '13800138001', receiverDetailAddress: '北京市海淀区中关村大街1号' },
  { id: 2, orderSn: 'ORD-20240528002', createTime: '2024-05-28T09:15:00', memberUsername: 'user_002', totalAmount: 14999, payType: 2, sourceType: 1, status: 1, orderType: 0, receiverName: '李四', receiverPhone: '13800138002', receiverDetailAddress: '上海市浦东新区陆家嘴环路2号' },
  { id: 3, orderSn: 'ORD-20240528003', createTime: '2024-05-28T08:45:00', memberUsername: 'user_003', totalAmount: 1899, payType: 1, sourceType: 0, status: 2, orderType: 0, receiverName: '王五', receiverPhone: '13800138003', receiverDetailAddress: '广州市天河区天河路3号' },
  { id: 4, orderSn: 'ORD-20240527004', createTime: '2024-05-27T22:10:00', memberUsername: 'user_004', totalAmount: 4799, payType: 0, sourceType: 0, status: 0, orderType: 0, receiverName: '赵六', receiverPhone: '13800138004', receiverDetailAddress: '深圳市南山区科技园4号' },
  { id: 5, orderSn: 'ORD-20240527005', createTime: '2024-05-27T18:30:00', memberUsername: 'user_005', totalAmount: 2999, payType: 2, sourceType: 1, status: 3, orderType: 0, receiverName: '钱七', receiverPhone: '13800138005', receiverDetailAddress: '杭州市西湖区文三路5号' },
  { id: 6, orderSn: 'ORD-20240527006', createTime: '2024-05-27T16:00:00', memberUsername: 'user_006', totalAmount: 6999, payType: 1, sourceType: 0, status: 4, orderType: 0, receiverName: '孙八', receiverPhone: '13800138006', receiverDetailAddress: '成都市高新区天府大道6号' },
  { id: 7, orderSn: 'ORD-20240526007', createTime: '2024-05-26T14:20:00', memberUsername: 'user_007', totalAmount: 5999, payType: 1, sourceType: 1, status: 1, orderType: 1, receiverName: '周九', receiverPhone: '13800138007', receiverDetailAddress: '武汉市洪山区光谷大道7号' },
  { id: 8, orderSn: 'ORD-20240526008', createTime: '2024-05-26T11:00:00', memberUsername: 'user_008', totalAmount: 899, payType: 2, sourceType: 0, status: 2, orderType: 0, receiverName: '吴十', receiverPhone: '13800138008', receiverDetailAddress: '南京市鼓楼区中山路8号' },
  { id: 9, orderSn: 'ORD-20240525009', createTime: '2024-05-25T20:00:00', memberUsername: 'user_009', totalAmount: 1299, payType: 1, sourceType: 1, status: 3, orderType: 0, receiverName: '郑十一', receiverPhone: '13800138009', receiverDetailAddress: '西安市雁塔区高新路9号' },
  { id: 10, orderSn: 'ORD-20240525010', createTime: '2024-05-25T15:30:00', memberUsername: 'user_010', totalAmount: 399, payType: 0, sourceType: 0, status: 0, orderType: 0, receiverName: '陈十二', receiverPhone: '13800138010', receiverDetailAddress: '重庆市渝北区红锦大道10号' },
])

const list = ref<OmsOrder[]>([...allList.value])
const total = ref(allList.value.length)
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

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.orderSn) result = result.filter(item => item.orderSn?.includes(listQuery.value.orderSn!))
  if (listQuery.value.receiverKeyword) result = result.filter(item => item.receiverName?.includes(listQuery.value.receiverKeyword!) || item.receiverPhone?.includes(listQuery.value.receiverKeyword!))
  if (listQuery.value.status !== undefined) result = result.filter(item => item.status === listQuery.value.status)
  if (listQuery.value.orderType !== undefined) result = result.filter(item => item.orderType === listQuery.value.orderType)
  if (listQuery.value.sourceType !== undefined) result = result.filter(item => item.sourceType === listQuery.value.sourceType)
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}

onMounted(() => { getList() })

const handleResetSearch = () => {
  listQuery.value = { orderSn: '', receiverKeyword: '', createTime: '', status: undefined, orderType: undefined, sourceType: undefined, pageNum: 1, pageSize: 10 }
  getList()
}

const handleSearchList = () => {
  listQuery.value.pageNum = 1
  getList()
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
  allList.value = allList.value.filter(item => item.id !== row.id)
  getList()
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

const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }

const handleCloseOrderConfirm = async () => {
  if (!closeOrderData.value.content) { ElMessage({ message: '操作备注不能为空', type: 'warning', duration: 1000 }); return }
  allList.value.filter(item => closeOrderData.value.orderIds.includes(item.id!)).forEach(item => { item.status = 4; item.note = closeOrderData.value.content })
  closeOrderData.value.dialogVisible = false
  closeOrderData.value.content = ''
  getList()
  ElMessage({ message: '关闭成功', type: 'success', duration: 1000 })
}

const deleteOrderFn = async (ids: number[]) => {
  await ElMessageBox.confirm('是否要进行该删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => !ids.includes(item.id!))
  getList()
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
