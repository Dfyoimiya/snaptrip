<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { couponTypes } from '@/utils/constant'

const router = useRouter()

const listQuery = ref({
  name: '',
  type: undefined as number | undefined,
  pageNum: 1,
  pageSize: 10,
})

const allList = ref([
  { id: 1, name: '全场满减券', type: 0, platform: 0, count: 1000, amount: 50, minPoint: 500, startTime: '2024-06-01T00:00:00', endTime: '2024-06-30T23:59:59', useType: 0, publishCount: 1000, useCount: 234, receiveCount: 567, enableTime: '2024-06-01T00:00:00' },
  { id: 2, name: '新会员注册礼', type: 3, platform: 0, count: 999, amount: 20, minPoint: 100, startTime: '2024-05-01T00:00:00', endTime: '2024-12-31T23:59:59', useType: 0, publishCount: 999, useCount: 156, receiveCount: 890, enableTime: '2024-05-01T00:00:00' },
  { id: 3, name: '618购物返券', type: 2, platform: 1, count: 500, amount: 30, minPoint: 300, startTime: '2024-06-10T00:00:00', endTime: '2024-06-20T23:59:59', useType: 0, publishCount: 500, useCount: 89, receiveCount: 234, enableTime: '2024-06-10T00:00:00' },
  { id: 4, name: '手机品类券', type: 2, platform: 0, count: 300, amount: 100, minPoint: 1000, startTime: '2024-06-01T00:00:00', endTime: '2024-06-30T23:59:59', useType: 2, publishCount: 300, useCount: 45, receiveCount: 123, enableTime: '2024-06-01T00:00:00' },
  { id: 5, name: '会员专享券', type: 1, platform: 0, count: 200, amount: 80, minPoint: 800, startTime: '2024-06-01T00:00:00', endTime: '2024-07-31T23:59:59', useType: 1, publishCount: 200, useCount: 34, receiveCount: 78, enableTime: '2024-06-01T00:00:00' },
  { id: 6, name: '数码分类券', type: 2, platform: 2, count: 400, amount: 60, minPoint: 600, startTime: '2024-06-15T00:00:00', endTime: '2024-07-15T23:59:59', useType: 1, publishCount: 400, useCount: 67, receiveCount: 189, enableTime: '2024-06-15T00:00:00' },
  { id: 7, name: '周年庆全场券', type: 0, platform: 0, count: 2000, amount: 100, minPoint: 1000, startTime: '2024-07-01T00:00:00', endTime: '2024-07-07T23:59:59', useType: 0, publishCount: 2000, useCount: 0, receiveCount: 0, enableTime: '2024-07-01T00:00:00' },
  { id: 8, name: '新人立减券', type: 3, platform: 1, count: 999, amount: 10, minPoint: 50, startTime: '2024-05-01T00:00:00', endTime: '2024-12-31T23:59:59', useType: 0, publishCount: 999, useCount: 345, receiveCount: 678, enableTime: '2024-05-01T00:00:00' },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.name) result = result.filter(item => item.name?.includes(listQuery.value.name))
  if (listQuery.value.type !== undefined) result = result.filter(item => item.type === listQuery.value.type)
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}
onMounted(() => { getList() })

const formatType = (value?: number) => couponTypes.find(item => item.value === value)?.label || ''
const formatPlatform = (value?: number) => value === 1 ? '移动平台' : value === 2 ? 'PC平台' : '全平台'
const formatUseType = (value?: number) => value === 1 ? '指定分类' : value === 2 ? '指定商品' : '全场通用'

const handleResetSearch = () => { listQuery.value = { name: '', type: undefined, pageNum: 1, pageSize: 10 }; getList() }
const handleSearchList = () => { listQuery.value.pageNum = 1; getList() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }
const handleAdd = () => { router.push('/sms/addCoupon') }
const handleView = (_index: number, row: any) => { router.push({ path: '/sms/couponDetail', query: { id: row.id } }) }
const handleUpdate = (_index: number, row: any) => { router.push({ path: '/sms/updateCoupon', query: { id: row.id } }) }
const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该优惠券?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => item.id !== row.id); getList(); ElMessage.success('删除成功!')
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
