<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { getTicketListAPI } from '@/apis/cs'
import type { CsTicket } from '@/types/cs'

const router = useRouter()

const listQuery = ref({
  status: '',
  priority: '',
  type: '',
  keyword: '',
  page: 1,
  page_size: 20,
})

const list = ref<CsTicket[]>([])
const total = ref(0)
const listLoading = ref(false)

const statusOptions = [
  { label: '待处理', value: 'open' },
  { label: '处理中', value: 'in_progress' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
]

const priorityOptions = [
  { label: '普通', value: 'normal' },
  { label: '紧急', value: 'urgent' },
  { label: '严重', value: 'critical' },
]

const typeOptions = [
  { label: '咨询', value: 'inquiry' },
  { label: '投诉', value: 'complaint' },
  { label: '退款', value: 'refund' },
  { label: '其他', value: 'other' },
]

const formatStatus = (s?: string) => statusOptions.find(o => o.value === s)?.label || s || '-'
const formatPriority = (p?: string) => priorityOptions.find(o => o.value === p)?.label || p || '-'
const formatType = (t?: string) => typeOptions.find(o => o.value === t)?.label || t || '-'

const priorityTagType = (p?: string) => {
  if (p === 'critical') return 'danger'
  if (p === 'urgent') return 'warning'
  return 'info'
}

const statusTagType = (s?: string) => {
  if (s === 'open') return 'danger'
  if (s === 'in_progress') return 'warning'
  if (s === 'resolved') return 'success'
  return 'info'
}

const fetchData = async () => {
  listLoading.value = true
  try {
    const res = await getTicketListAPI({
      status: listQuery.value.status || undefined,
      priority: listQuery.value.priority || undefined,
      type: listQuery.value.type || undefined,
      keyword: listQuery.value.keyword || undefined,
      page: listQuery.value.page,
      page_size: listQuery.value.page_size,
    })
    list.value = (res.data as any)?.items || []
    total.value = (res.data as any)?.total || 0
  } catch {
    ElMessage.error('获取工单列表失败')
  } finally {
    listLoading.value = false
  }
}

const handleSearch = () => {
  listQuery.value.page = 1
  fetchData()
}

const handleReset = () => {
  listQuery.value = { status: '', priority: '', type: '', keyword: '', page: 1, page_size: 20 }
  fetchData()
}

const handleDetail = (id: string) => {
  router.push({ name: 'csTicketDetail', params: { id } })
}

const handlePageChange = (page: number) => {
  listQuery.value.page = page
  fetchData()
}

const handleSizeChange = (size: number) => {
  listQuery.value.page_size = size
  listQuery.value.page = 1
  fetchData()
}

onMounted(() => fetchData())
</script>

<template>
  <div class="cs-ticket-container">
    <div class="search-bar">
      <el-card>
        <el-form :inline="true" :model="listQuery" size="small">
          <el-form-item label="状态">
            <el-select v-model="listQuery.status" placeholder="全部" clearable>
              <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="listQuery.priority" placeholder="全部" clearable>
              <el-option v-for="o in priorityOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="listQuery.type" placeholder="全部" clearable>
              <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input v-model="listQuery.keyword" placeholder="标题/描述" clearable @keyup.enter="handleSearch" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div class="table-container">
      <el-card>
        <el-table :data="list" v-loading="listLoading" border stripe style="width: 100%">
          <el-table-column label="标题" prop="title" min-width="180" show-overflow-tooltip />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">{{ formatType(row.type) }}</template>
          </el-table-column>
          <el-table-column label="优先级" width="80">
            <template #default="{ row }">
              <el-tag :type="priorityTagType(row.priority)" size="small">{{ formatPriority(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="handleDetail(row.id!)">处理</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="listQuery.page"
            v-model:page-size="listQuery.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.cs-ticket-container {
  padding: 16px;
}

.search-bar {
  margin-bottom: 16px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
