<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchBannerList, saveBanner, deleteBanner, updateBannerStatus } from '@/apis/banner'
import type { SmsHomeAdvertise } from '@/types/banner'

const loading = ref(false)
const list = ref<SmsHomeAdvertise[]>([])
const search = reactive({
  name: '',
  type: '' as number | '',
})
const selectedIds = ref<number[]>([])

const filteredList = computed(() => {
  let result = list.value
  if (search.name) {
    result = result.filter(item => item.name?.includes(search.name))
  }
  if (search.type !== '') {
    result = result.filter(item => item.type === search.type)
  }
  return result
})

async function loadList() {
  loading.value = true
  try {
    const res = await fetchBannerList({})
    list.value = res.data.list
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  search.name = ''
  search.type = ''
}

function handleSelectionChange(selection: SmsHomeAdvertise[]) {
  selectedIds.value = selection.map(item => item.id!).filter(Boolean)
}

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('添加广告')
const form = reactive<SmsHomeAdvertise>({
  id: undefined,
  name: '',
  type: 0,
  pic: '',
  startTime: '',
  endTime: '',
  status: 1,
  url: '',
  note: '',
  sort: 100,
})
const formRef = ref()
const rules = {
  name: [{ required: true, message: '请输入广告名称', trigger: 'blur' }],
  pic: [{ required: true, message: '请输入图片链接', trigger: 'blur' }],
  startTime: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  endTime: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

function handleAdd() {
  dialogTitle.value = '添加广告'
  Object.assign(form, {
    id: undefined,
    name: '',
    type: 0,
    pic: '',
    startTime: '',
    endTime: '',
    status: 1,
    url: '',
    note: '',
    sort: 100,
  })
  dialogVisible.value = true
}

function handleEdit(row: SmsHomeAdvertise) {
  dialogTitle.value = '编辑广告'
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  await saveBanner({ ...form })
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadList()
}

async function handleDelete(row: SmsHomeAdvertise) {
  try {
    await ElMessageBox.confirm(`确定删除广告"${row.name}"吗？`, '提示', { type: 'warning' })
    await deleteBanner(row.id!)
    ElMessage.success('删除成功')
    loadList()
  } catch {
    // cancel
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请至少选择一项')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 项吗？`, '提示', { type: 'warning' })
    for (const id of selectedIds.value) {
      await deleteBanner(id)
    }
    ElMessage.success('批量删除成功')
    loadList()
  } catch {
    // cancel
  }
}

async function handleToggleStatus(row: SmsHomeAdvertise) {
  const newStatus = row.status === 1 ? 0 : 1
  await updateBannerStatus(row.id!, newStatus)
  row.status = newStatus
  ElMessage.success('状态更新成功')
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="search" inline>
        <el-form-item label="广告名称">
          <el-input v-model="search.name" placeholder="广告名称" clearable />
        </el-form-item>
        <el-form-item label="广告位置">
          <el-select v-model="search.type" placeholder="全部位置" clearable style="width: 120px">
            <el-option label="PC端" :value="0" />
            <el-option label="APP端" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">
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
          <span>轮播广告列表</span>
          <div>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>批量删除
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd" style="margin-left: 8px">
              <el-icon><Plus /></el-icon>添加广告
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="filteredList"
        border
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="广告图片" width="160" align="center">
          <template #default="{ row }">
            <el-image :src="row.pic" fit="cover" style="width: 140px; height: 56px; border-radius: 4px" />
          </template>
        </el-table-column>
        <el-table-column label="广告名称" prop="name" min-width="160" show-overflow-tooltip />
        <el-table-column label="广告位置" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.type === 0" type="primary" size="small">PC端</el-tag>
            <el-tag v-else type="success" size="small">APP端</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="投放时间" width="200" align="center">
          <template #default="{ row }">
            <div>{{ row.startTime }}</div>
            <div style="color: #909399; font-size: 12px">至</div>
            <div>{{ row.endTime }}</div>
          </template>
        </el-table-column>
        <el-table-column label="上线/下线" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="点击次数" prop="clickCount" width="90" align="center" />
        <el-table-column label="订单数" prop="orderCount" width="80" align="center" />
        <el-table-column label="排序" prop="sort" width="70" align="center" />
        <el-table-column label="操作" width="180" fixed="right" align="center">
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

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="广告名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入广告名称" />
        </el-form-item>
        <el-form-item label="广告位置">
          <el-radio-group v-model="form.type">
            <el-radio :label="0">PC端</el-radio>
            <el-radio :label="1">APP端</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="图片链接" prop="pic">
          <el-input v-model="form.pic" placeholder="请输入图片URL地址" />
        </el-form-item>
        <el-form-item label="开始时间" prop="startTime">
          <el-date-picker v-model="form.startTime" type="datetime" placeholder="选择开始时间" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="endTime">
          <el-date-picker v-model="form.endTime" type="datetime" placeholder="选择结束时间" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="form.url" placeholder="请输入点击跳转的链接地址" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="备注信息" />
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
