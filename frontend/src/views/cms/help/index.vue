<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHelpListAPI, helpCreateAPI, helpUpdateByIdAPI, helpDeleteByIdAPI } from '@/apis/help'
import type { CmsHelp } from '@/types/help'

const loading = ref(false)
const list = ref<CmsHelp[]>([])
const total = ref(0)
const search = reactive({
  categoryName: '',
  status: '' as number | '',
})
const page = reactive({ page: 1, page_size: 20 })
const selectedIds = ref<number[]>([])

async function loadList() {
  loading.value = true
  try {
    const res = await getHelpListAPI({
      page: page.page,
      page_size: page.page_size,
      category_name: search.categoryName || undefined,
      status: search.status !== '' ? search.status : undefined,
    })
    list.value = res.data.items || []
    total.value = res.data.total || 0
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  search.categoryName = ''
  search.status = ''
  loadList()
}

function handleSelectionChange(selection: CmsHelp[]) {
  selectedIds.value = selection.map(item => item.id!).filter(Boolean)
}

function handleSizeChange(size: number) {
  page.page_size = size
  loadList()
}

function handlePageChange(p: number) {
  page.page = p
  loadList()
}

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('添加帮助')
const form = reactive<CmsHelp>({
  id: undefined,
  title: '',
  content: '',
  categoryName: '',
  status: 1,
  sort: 0,
})
const formRef = ref()
const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  categoryName: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

function handleAdd() {
  dialogTitle.value = '添加帮助'
  Object.assign(form, {
    id: undefined,
    title: '',
    content: '',
    categoryName: '',
    status: 1,
    sort: 0,
  })
  dialogVisible.value = true
}

function handleEdit(row: CmsHelp) {
  dialogTitle.value = '编辑帮助'
  Object.assign(form, {
    id: row.id,
    title: row.title || '',
    content: row.content || '',
    categoryName: row.categoryName || '',
    status: row.status ?? 1,
    sort: row.sort ?? 0,
  })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (form.id) {
    await helpUpdateByIdAPI(form.id, form)
  } else {
    await helpCreateAPI(form)
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadList()
}

async function handleDelete(row: CmsHelp) {
  try {
    await ElMessageBox.confirm(`确定删除"${row.title}"吗？`, '提示', { type: 'warning' })
    await helpDeleteByIdAPI(row.id!)
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
      await helpDeleteByIdAPI(id)
    }
    ElMessage.success('批量删除成功')
    loadList()
  } catch {
    // cancel
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
        <el-form-item label="分类名称">
          <el-input v-model="search.categoryName" placeholder="分类名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="展示" :value="1" />
            <el-option label="隐藏" :value="0" />
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
          <span>帮助管理列表</span>
          <div>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>批量删除
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd" style="margin-left: 8px">
              <el-icon><Plus /></el-icon>添加帮助
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="list"
        border
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="编号" prop="id" width="80" align="center" show-overflow-tooltip />
        <el-table-column label="标题" prop="title" min-width="200" show-overflow-tooltip />
        <el-table-column label="分类" prop="categoryName" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.categoryName || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" prop="sort" width="80" align="center" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '展示' : '隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="createdAt" width="180" align="center" />
        <el-table-column label="操作" width="160" fixed="right" align="center">
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

      <el-pagination
        v-if="total > 0"
        style="margin-top: 16px; justify-content: flex-end"
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :page-size="page.page_size"
        :current-page="page.page"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="分类名称" prop="categoryName">
          <el-input v-model="form.categoryName" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" placeholder="排序值" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :label="1">展示</el-radio>
            <el-radio :label="0">隐藏</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="帮助内容（支持Markdown）" />
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
