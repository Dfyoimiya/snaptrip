<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { couponTypes } from '@/utils/constant'
import { getCouponListAPI, deleteCouponByIdAPI } from '@/apis/coupon'

const router = useRouter()

const listQuery = ref({
  name: '',
  type: undefined as number | undefined,
  pageNum: 1,
  pageSize: 10,
})

const list = ref<any[]>([])
const total = ref(0)
const listLoading = ref(false)

async function fetchData() {
  listLoading.value = true
  try {
    const res = await getCouponListAPI(listQuery.value)
    list.value = res.list || []
    total.value = res.total || 0
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchData() })

const formatType = (value?: number) => couponTypes.find(item => item.value === value)?.label || ''
const formatPlatform = (value?: number) => value === 1 ? '移动平台' : value === 2 ? 'PC平台' : '全平台'
const formatUseType = (value?: number) => value === 1 ? '指定分类' : value === 2 ? '指定商品' : '全场通用'

const handleResetSearch = () => { listQuery.value = { name: '', type: undefined, pageNum: 1, pageSize: 10 }; fetchData() }
const handleSearchList = () => { listQuery.value.pageNum = 1; fetchData() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; fetchData() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; fetchData() }
const handleAdd = () => { router.push('/sms/addCoupon') }
const handleView = (_index: number, row: any) => { router.push({ path: '/sms/couponDetail', query: { id: row.id } }) }
const handleUpdate = (_index: number, row: any) => { router.push({ path: '/sms/updateCoupon', query: { id: row.id } }) }
const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该优惠券?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  await deleteCouponByIdAPI(row.id)
  ElMessage.success('删除成功!')
  fetchData()
}
</script>

<template>
  <div class="app-container">
    <el-card class="filter-container" shadow="never">
      <div>
        <el-icon class="el-icon-middle"><Search /></el-icon>
        <span>筛选搜索</span>
        <el-button style="float: right" @click="handleSearchList" type="primary">查询搜索</el-button>
        <el-button style="float: right; margin-right: 15px" @click="handleResetSearch">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="优惠券名称：">
            <el-input v-model="listQuery.name" class="input-width" placeholder="优惠券名称" clearable />
          </el-form-item>
          <el-form-item label="优惠券类型：">
            <el-select v-model="listQuery.type" placeholder="全部" clearable class="input-width">
              <el-option v-for="item in couponTypes" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button class="btn-add" @click="handleAdd">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="couponTable" :data="list" style="width: 100%;" v-loading="listLoading" border>
        <el-table-column label="编号" width="80" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="优惠券名称" align="center"><template #default="scope">{{ scope.row.name }}</template></el-table-column>
        <el-table-column label="优惠券类型" width="120" align="center"><template #default="scope">{{ formatType(scope.row.type) }}</template></el-table-column>
        <el-table-column label="可使用商品" width="120" align="center"><template #default="scope">{{ formatUseType(scope.row.useType) }}</template></el-table-column>
        <el-table-column label="使用门槛" width="120" align="center"><template #default="scope">满{{ scope.row.minPoint }}元可用</template></el-table-column>
        <el-table-column label="面值" width="80" align="center"><template #default="scope">{{ scope.row.amount }}元</template></el-table-column>
        <el-table-column label="适用平台" width="100" align="center"><template #default="scope">{{ formatPlatform(scope.row.platform) }}</template></el-table-column>
        <el-table-column label="有效期" width="280" align="center">
          <template #default="scope">{{ formatDateTime(scope.row.startTime) }} 至 {{ formatDateTime(scope.row.endTime) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.endTime && new Date(scope.row.endTime) < new Date() ? 'info' : 'success'" size="small">
              {{ scope.row.endTime && new Date(scope.row.endTime) < new Date() ? '已过期' : '未过期' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="scope">
            <el-button size="small" @click="handleView(scope.$index, scope.row)">查看</el-button>
            <el-button size="small" @click="handleUpdate(scope.$index, scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>
  </div>
</template>

<style scoped>
.input-width { width: 203px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
