<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'
import { getMemberListAPI, getMemberDetailAPI, toggleMemberStatusAPI } from '@/apis/member'

interface MemberItem {
  id: string
  email: string
  is_active: boolean
  created_at: string | null
}

const search = reactive({
  keyword: '',
  is_active: undefined as boolean | undefined,
})
const list = ref<MemberItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const currentDetail = ref<Record<string, any> | null>(null)

const filteredList = computed(() => list.value)

async function loadList() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (search.keyword) params.keyword = search.keyword
    if (search.is_active !== undefined) params.is_active = search.is_active
    const res = await getMemberListAPI(params)
    const data = res.data as any
    list.value = (data?.items || data?.list || []) as MemberItem[]
    total.value = data?.total || 0
  } catch {
    ElMessage.error('加载会员列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  search.keyword = ''
  search.is_active = undefined
  page.value = 1
  loadList()
}

async function handleViewDetail(row: MemberItem) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res = await getMemberDetailAPI(row.id)
    currentDetail.value = (res as any).data || (res as any)
  } catch {
    ElMessage.error('加载会员详情失败')
    currentDetail.value = null
  } finally {
    detailLoading.value = false
  }
}

async function handleToggleStatus(row: MemberItem) {
  const newStatus = !row.is_active
  const label = newStatus ? '启用' : '封禁'
  try {
    await ElMessageBox.confirm(`确定${label}该会员吗？`, '提示', { type: 'warning' })
    await toggleMemberStatusAPI(row.id, newStatus)
    row.is_active = newStatus
    ElMessage.success(`已${label}`)
  } catch {
    // cancel or error
  }
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="search" inline>
        <el-form-item label="邮箱搜索">
          <el-input v-model="search.keyword" placeholder="输入邮箱" clearable style="width: 240px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.is_active" placeholder="全部" clearable style="width: 100px">
            <el-option label="启用" :value="true" />
            <el-option label="封禁" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>会员列表</span>
          <span style="color: #909399; font-size: 13px">共 {{ total }} 位会员</span>
        </div>
      </template>

      <el-table v-loading="loading" :data="filteredList" border style="width: 100%">
        <el-table-column label="会员ID" prop="id" min-width="200" show-overflow-tooltip />
        <el-table-column label="邮箱" prop="email" min-width="200" />
        <el-table-column label="注册时间" width="180" align="center">
          <template #default="{ row }">
            {{ row.created_at ? formatDateTime(row.created_at) : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              @change="handleToggleStatus(row as MemberItem)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleViewDetail(row as MemberItem)">
              <el-icon><View /></el-icon>详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadList"
          @size-change="loadList"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="会员详情" width="500px" destroy-on-close>
      <div v-loading="detailLoading">
        <el-descriptions v-if="currentDetail" :column="1" border>
          <el-descriptions-item label="会员ID">{{ currentDetail.id }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentDetail.email }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ currentDetail.nickname || '--' }}</el-descriptions-item>
          <el-descriptions-item label="头像">
            <el-avatar v-if="currentDetail.avatar_url" :src="currentDetail.avatar_url" :size="48" />
            <span v-else>--</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentDetail.is_active ? 'success' : 'danger'">
              {{ currentDetail.is_active ? '启用' : '封禁' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ currentDetail.created_at ? formatDateTime(currentDetail.created_at) : '--' }}</el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="暂无数据" />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.app-container {
  padding: 20px;
}
.search-card {
  :deep(.el-card__body) {
    padding-bottom: 0;
  }
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
