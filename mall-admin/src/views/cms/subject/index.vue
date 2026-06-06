<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchSubjectList,
  fetchSubjectCategoryList,
  saveSubject,
  deleteSubject,
  updateSubjectRecommendStatus,
  updateSubjectShowStatus,
} from '@/apis/subject'
import type { CmsSubject, CmsSubjectCategory } from '@/types/subject'

const loading = ref(false)
const list = ref<CmsSubject[]>([])
const categoryList = ref<CmsSubjectCategory[]>([])
const search = reactive({
  title: '',
  recommendStatus: '' as number | '',
})
const selectedIds = ref<number[]>([])

const filteredList = computed(() => {
  let result = list.value
  if (search.title) {
    result = result.filter(item => item.title?.includes(search.title))
  }
  if (search.recommendStatus !== '') {
    result = result.filter(item => item.recommendStatus === search.recommendStatus)
  }
  return result
})

async function loadList() {
  loading.value = true
  try {
    const [subjectRes, categoryRes] = await Promise.all([
      fetchSubjectList({}),
      fetchSubjectCategoryList(),
    ])
    list.value = subjectRes.data.list
    categoryList.value = categoryRes.data
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  search.title = ''
  search.recommendStatus = ''
}

function handleSelectionChange(selection: CmsSubject[]) {
  selectedIds.value = selection.map(item => item.id!).filter(Boolean)
}

function getCategoryName(categoryId?: number) {
  const cat = categoryList.value.find(c => c.id === categoryId)
  return cat?.name || '-'
}

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('添加专题')
const form = reactive<CmsSubject>({
  id: undefined,
  categoryId: undefined,
  title: '',
  pic: '',
  description: '',
  recommendStatus: 1,
  showStatus: 1,
})
const formRef = ref()
const rules = {
  title: [{ required: true, message: '请输入专题名称', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择专题分类', trigger: 'change' }],
  pic: [{ required: true, message: '请输入专题图片链接', trigger: 'blur' }],
}

function handleAdd() {
  dialogTitle.value = '添加专题'
  Object.assign(form, {
    id: undefined,
    categoryId: undefined,
    title: '',
    pic: '',
    description: '',
    recommendStatus: 1,
    showStatus: 1,
  })
  dialogVisible.value = true
}

function handleEdit(row: CmsSubject) {
  dialogTitle.value = '编辑专题'
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const category = categoryList.value.find(c => c.id === form.categoryId)
  await saveSubject({ ...form, categoryName: category?.name })
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadList()
}

async function handleDelete(row: CmsSubject) {
  try {
    await ElMessageBox.confirm(`确定删除专题"${row.title}"吗？`, '提示', { type: 'warning' })
    await deleteSubject(row.id!)
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
      await deleteSubject(id)
    }
    ElMessage.success('批量删除成功')
    loadList()
  } catch {
    // cancel
  }
}

async function handleToggleRecommend(row: CmsSubject) {
  const newStatus = row.recommendStatus === 1 ? 0 : 1
  await updateSubjectRecommendStatus(row.id!, newStatus)
  row.recommendStatus = newStatus
  ElMessage.success('状态更新成功')
}

async function handleToggleShow(row: CmsSubject) {
  const newStatus = row.showStatus === 1 ? 0 : 1
  await updateSubjectShowStatus(row.id!, newStatus)
  row.showStatus = newStatus
  ElMessage.success('展示状态更新成功')
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="search" inline>
        <el-form-item label="专题名称">
          <el-input v-model="search.title" placeholder="专题名称" clearable />
        </el-form-item>
        <el-form-item label="推荐状态">
          <el-select v-model="search.recommendStatus" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="推荐中" :value="1" />
            <el-option label="未推荐" :value="0" />
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
          <span>专题管理列表</span>
          <div>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>批量删除
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd" style="margin-left: 8px">
              <el-icon><Plus /></el-icon>添加专题
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
        <el-table-column label="专题图片" width="120" align="center">
          <template #default="{ row }">
            <el-image :src="row.pic" fit="cover" style="width: 100px; height: 75px; border-radius: 4px" />
          </template>
        </el-table-column>
        <el-table-column label="专题名称" prop="title" min-width="160" show-overflow-tooltip />
        <el-table-column label="所属分类" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryName(row.categoryId) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="推荐" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.recommendStatus"
              :active-value="1"
              :inactive-value="0"
              @change="handleToggleRecommend(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="展示" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.showStatus"
              :active-value="1"
              :inactive-value="0"
              @change="handleToggleShow(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="商品数" prop="productCount" width="80" align="center" />
        <el-table-column label="阅读量" prop="readCount" width="90" align="center" />
        <el-table-column label="收藏" prop="collectCount" width="80" align="center" />
        <el-table-column label="评论" prop="commentCount" width="80" align="center" />
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
        <el-form-item label="专题名称" prop="title">
          <el-input v-model="form.title" placeholder="请输入专题名称" />
        </el-form-item>
        <el-form-item label="所属分类" prop="categoryId">
          <el-select v-model="form.categoryId" placeholder="选择专题分类" style="width: 100%">
            <el-option
              v-for="cat in categoryList"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id!"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="专题图片" prop="pic">
          <el-input v-model="form.pic" placeholder="请输入专题封面图片URL" />
        </el-form-item>
        <el-form-item label="专题描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入专题描述" />
        </el-form-item>
        <el-form-item label="推荐状态">
          <el-radio-group v-model="form.recommendStatus">
            <el-radio :label="1">推荐</el-radio>
            <el-radio :label="0">不推荐</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="展示状态">
          <el-radio-group v-model="form.showStatus">
            <el-radio :label="1">展示</el-radio>
            <el-radio :label="0">不展示</el-radio>
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
