<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'

// 会员数据
const allMembers = ref([
  { id: 1, username: 'zhangsan', nickname: '张三', phone: '13800138001', email: 'zhangsan@example.com', gender: 1, birthday: '1990-05-20', status: 1, source: 'PC注册', integration: 1250, createTime: '2025-01-15T10:30:00' },
  { id: 2, username: 'lisi', nickname: '李四', phone: '13800138002', email: 'lisi@example.com', gender: 0, birthday: '1992-08-15', status: 1, source: '小程序', integration: 860, createTime: '2025-02-10T14:20:00' },
  { id: 3, username: 'wangwu', nickname: '王五', phone: '13800138003', email: 'wangwu@example.com', gender: 1, birthday: '1988-12-01', status: 0, source: 'APP', integration: 2300, createTime: '2024-12-20T09:00:00' },
  { id: 4, username: 'zhaoliu', nickname: '赵六', phone: '13800138004', email: 'zhaoliu@example.com', gender: 0, birthday: '1995-03-08', status: 1, source: 'PC注册', integration: 450, createTime: '2025-03-05T16:45:00' },
  { id: 5, username: 'qianqi', nickname: '钱七', phone: '13800138005', email: 'qianqi@example.com', gender: 1, birthday: '1993-07-22', status: 1, source: '小程序', integration: 1680, createTime: '2025-01-28T11:10:00' },
  { id: 6, username: 'sunba', nickname: '孙八', phone: '13800138006', email: 'sunba@example.com', gender: 0, birthday: '1991-11-11', status: 1, source: 'APP', integration: 720, createTime: '2025-04-12T08:30:00' },
  { id: 7, username: 'zhoujiu', nickname: '周九', phone: '13800138007', email: 'zhoujiu@example.com', gender: 1, birthday: '1989-09-09', status: 0, source: 'PC注册', integration: 3100, createTime: '2024-11-08T13:00:00' },
  { id: 8, username: 'wushi', nickname: '吴十', phone: '13800138008', email: 'wushi@example.com', gender: 0, birthday: '1994-04-04', status: 1, source: '小程序', integration: 560, createTime: '2025-05-01T10:00:00' },
  { id: 9, username: 'zhengyi', nickname: '郑一', phone: '13800138009', email: 'zhengyi@example.com', gender: 1, birthday: '1996-06-18', status: 1, source: 'APP', integration: 920, createTime: '2025-03-22T15:20:00' },
  { id: 10, username: 'fanger', nickname: '冯二', phone: '13800138010', email: 'fanger@example.com', gender: 0, birthday: '1987-10-10', status: 1, source: 'PC注册', integration: 2750, createTime: '2024-10-15T09:45:00' },
])

const search = reactive({
  keyword: '',
  status: '' as number | '',
})
const list = ref([...allMembers.value])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('编辑会员')
const memberForm = reactive({
  id: undefined as number | undefined,
  nickname: '',
  phone: '',
  email: '',
  gender: 1,
  status: 1,
  integration: 0,
})
const formRef = ref()

const rules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
}

const filteredList = computed(() => {
  let result = list.value
  if (search.keyword) {
    result = result.filter(item =>
      item.username?.includes(search.keyword) ||
      item.nickname?.includes(search.keyword) ||
      item.phone?.includes(search.keyword)
    )
  }
  if (search.status !== '') {
    result = result.filter(item => item.status === search.status)
  }
  return result
})

function handleSearch() {
  list.value = [...allMembers.value]
  let result = [...list.value]
  if (search.keyword) {
    result = result.filter(item =>
      item.username?.includes(search.keyword) ||
      item.nickname?.includes(search.keyword) ||
      item.phone?.includes(search.keyword)
    )
  }
  if (search.status !== '') {
    result = result.filter(item => item.status === search.status)
  }
  list.value = result
}

function handleReset() {
  search.keyword = ''
  search.status = ''
  list.value = [...allMembers.value]
}

function handleEdit(row: any) {
  dialogTitle.value = '编辑会员'
  Object.assign(memberForm, {
    id: row.id,
    nickname: row.nickname,
    phone: row.phone,
    email: row.email,
    gender: row.gender,
    status: row.status,
    integration: row.integration,
  })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const idx = allMembers.value.findIndex(m => m.id === memberForm.id)
  if (idx > -1) {
    Object.assign(allMembers.value[idx], memberForm)
    ElMessage.success('修改成功')
  }
  dialogVisible.value = false
  handleSearch()
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 1 ? 0 : 1
  row.status = newStatus
  const idx = allMembers.value.findIndex(m => m.id === row.id)
  if (idx > -1) allMembers.value[idx].status = newStatus
  ElMessage.success(newStatus === 1 ? '已启用' : '已禁用')
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除会员"${row.nickname}"吗？`, '提示', { type: 'warning' })
    const idx = allMembers.value.findIndex(m => m.id === row.id)
    if (idx > -1) allMembers.value.splice(idx, 1)
    list.value = allMembers.value.filter(m => {
      if (search.keyword && !m.nickname?.includes(search.keyword) && !m.username?.includes(search.keyword)) return false
      if (search.status !== '' && m.status !== search.status) return false
      return true
    })
    ElMessage.success('删除成功')
  } catch {
    // cancel
  }
}

onMounted(() => {
  list.value = [...allMembers.value]
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="search" inline>
        <el-form-item label="搜索">
          <el-input v-model="search.keyword" placeholder="帐号/昵称/手机号" clearable style="width: 220px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部" clearable style="width: 100px">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
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
          <span style="color: #909399; font-size: 13px">共 {{ filteredList.length }} 位会员</span>
        </div>
      </template>

      <el-table v-loading="loading" :data="filteredList" border style="width: 100%">
        <el-table-column label="编号" prop="id" width="60" align="center" />
        <el-table-column label="帐号" prop="username" width="120" />
        <el-table-column label="昵称" prop="nickname" width="120" />
        <el-table-column label="手机号" prop="phone" width="130" />
        <el-table-column label="邮箱" prop="email" min-width="160" show-overflow-tooltip />
        <el-table-column label="性别" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.gender === 1" size="small" type="primary">男</el-tag>
            <el-tag v-else size="small" type="danger">女</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="积分" prop="integration" width="80" align="center" />
        <el-table-column label="来源" prop="source" width="90" align="center" />
        <el-table-column label="注册时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.createTime) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form ref="formRef" :model="memberForm" :rules="rules" label-width="80px">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="memberForm.nickname" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="memberForm.email" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="memberForm.gender">
            <el-radio :label="1">男</el-radio>
            <el-radio :label="0">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="积分">
          <el-input-number v-model="memberForm.integration" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="memberForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">确定</el-button>
      </template>
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
