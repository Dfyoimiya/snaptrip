<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()

const defaultStatusOptions = [
  { label: '待处理', value: 0 },
  { label: '退货中', value: 1 },
  { label: '已完成', value: 2 },
  { label: '已拒绝', value: 3 },
]

const listQuery = ref({
  id: undefined as number | undefined,
  status: undefined as number | undefined,
  createTime: '',
  handleMan: '',
  handleTime: '',
  pageNum: 1,
  pageSize: 10,
})

const statusOptions = ref([...defaultStatusOptions])

const allList = ref([
  { id: 1, createTime: '2024-05-28T10:30:00', memberUsername: 'user_001', productRealPrice: 9999, productCount: 1, status: 0 },
  { id: 2, createTime: '2024-05-27T14:20:00', memberUsername: 'user_002', productRealPrice: 6999, productCount: 1, status: 0 },
  { id: 3, createTime: '2024-05-26T09:10:00', memberUsername: 'user_003', productRealPrice: 1899, productCount: 2, status: 1 },
  { id: 4, createTime: '2024-05-25T16:45:00', memberUsername: 'user_004', productRealPrice: 5999, productCount: 1, status: 1 },
  { id: 5, createTime: '2024-05-24T11:30:00', memberUsername: 'user_005', productRealPrice: 399, productCount: 3, status: 2 },
  { id: 6, createTime: '2024-05-23T20:00:00', memberUsername: 'user_006', productRealPrice: 1299, productCount: 1, status: 2 },
  { id: 7, createTime: '2024-05-22T08:15:00', memberUsername: 'user_007', productRealPrice: 899, productCount: 1, status: 3 },
  { id: 8, createTime: '2024-05-21T13:40:00', memberUsername: 'user_008', productRealPrice: 1488, productCount: 2, status: 3 },
  { id: 9, createTime: '2024-05-20T17:25:00', memberUsername: 'user_009', productRealPrice: 4799, productCount: 1, status: 0 },
  { id: 10, createTime: '2024-05-19T22:10:00', memberUsername: 'user_010', productRealPrice: 2999, productCount: 1, status: 2 },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)
const multipleSelection = ref<any[]>([])
const operateType = ref<number>()

const operateOptions = ref([{ label: '批量删除', value: 1 }])

const formatStatus = (status?: number) => defaultStatusOptions.find(item => item.value === status)?.label || ''
const formatReturnAmount = (row: any) => (row.productRealPrice || 0) * (row.productCount || 0)

const handleSelectionChange = (val: any[]) => { multipleSelection.value = val }

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.id !== undefined) result = result.filter(item => item.id === listQuery.value.id)
  if (listQuery.value.status !== undefined) result = result.filter(item => item.status === listQuery.value.status)
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}

onMounted(() => { getList() })

const handleResetSearch = () => { listQuery.value = { id: undefined, status: undefined, createTime: '', handleMan: '', handleTime: '', pageNum: 1, pageSize: 10 }; getList() }
const handleSearchList = () => { listQuery.value.pageNum = 1; getList() }
const handleViewDetail = (_index: number, row: any) => { router.push({ path: '/oms/returnApplyDetail', query: { id: row.id } }) }

const handleBatchOperate = async () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) { ElMessage({ message: '请选择要操作的申请', type: 'warning', duration: 1000 }); return }
  if (operateType.value === 1) {
    await ElMessageBox.confirm('是否要进行删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const ids = multipleSelection.value.map(item => item.id)
    allList.value = allList.value.filter(item => !ids.includes(item.id))
    getList()
    ElMessage({ type: 'success', message: '删除成功!' })
  }
}

const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }
</script>

<template>
  <div class="app-container">
    <el-card class="filter-container" shadow="never">
      <div>
        <el-icon class="el-icon-middle"><Search /></el-icon>
        <span>筛选搜索</span>
        <el-button style="float:right" type="primary" @click="handleSearchList()">查询搜索</el-button>
        <el-button style="float:right;margin-right: 15px" @click="handleResetSearch()">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="输入搜索：">
            <el-input v-model="listQuery.id" class="input-width" placeholder="服务单号"></el-input>
          </el-form-item>
          <el-form-item label="处理状态：">
            <el-select v-model="listQuery.status" placeholder="全部" clearable class="input-width">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="申请时间：">
            <el-date-picker class="input-width" v-model="listQuery.createTime" value-format="YYYY-MM-DD" type="date" placeholder="请选择时间"></el-date-picker>
          </el-form-item>
          <el-form-item label="操作人员：">
            <el-input v-model="listQuery.handleMan" class="input-width" placeholder="全部"></el-input>
          </el-form-item>
          <el-form-item label="处理时间：">
            <el-date-picker class="input-width" v-model="listQuery.handleTime" value-format="YYYY-MM-DD" type="date" placeholder="请选择时间"></el-date-picker>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
    </el-card>
    <div class="table-container">
      <el-table ref="returnApplyTable" :data="list" style="width: 100%;" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center"></el-table-column>
        <el-table-column label="服务单号" width="180" align="center">
          <template #default="scope">{{ scope.row.id }}</template>
        </el-table-column>
        <el-table-column label="申请时间" width="180" align="center">
          <template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template>
        </el-table-column>
        <el-table-column label="用户账号" align="center">
          <template #default="scope">{{ scope.row.memberUsername }}</template>
        </el-table-column>
        <el-table-column label="退款金额" width="180" align="center">
          <template #default="scope">￥{{ formatReturnAmount(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="申请状态" width="180" align="center">
          <template #default="scope">{{ formatStatus(scope.row.status) }}</template>
        </el-table-column>
        <el-table-column label="处理时间" width="180" align="center">
          <template #default="scope">{{ formatDateTime(scope.row.handleTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="scope">
            <el-button size="small" @click="handleViewDetail(scope.$index, scope.row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="batch-operate-container">
      <el-select v-model="operateType" placeholder="批量操作">
        <el-option v-for="item in operateOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
      </el-select>
      <el-button style="margin-left: 20px" class="search-button" @click="handleBatchOperate()" type="primary">确定</el-button>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total"></el-pagination>
    </div>
  </div>
</template>

<style scoped>
.input-width { width: 203px }
.batch-operate-container { display: inline-block; margin-top: 12px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
