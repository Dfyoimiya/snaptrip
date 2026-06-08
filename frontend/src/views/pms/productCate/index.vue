<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Bottom, Top, View } from '@element-plus/icons-vue'
import { getProductCategoryListWithChildrenAPI, createProductCategoryAPI, updateProductCategoryAPI, productCategoryDeleteByIdAPI, productCategoryUpdateNavStatusAPI, productCategoryUpdateShowStatusAPI } from '@/apis/productCate'

// 分类数据（树形）
const cateList = ref<any[]>([])
const listLoading = ref(false)

async function fetchData() {
  listLoading.value = true
  try {
    const res = await getProductCategoryListWithChildrenAPI()
    cateList.value = res || []
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchData() })

const dialogVisible = ref(false)
const dialogTitle = ref('')
const cateForm = ref({ id: undefined as number | undefined, parentId: 0, name: '', productUnit: '', sort: 0, navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' })
const parentOptions = ref([{ label: '无上级分类', value: 0 }])

// 递归提取父级选项
function extractParentOptions(list: any[], level = 0) {
  const result: any[] = []
  list.forEach(item => {
    result.push({ label: '  '.repeat(level) + item.name, value: item.id })
    if (item.children && item.children.length > 0) {
      result.push(...extractParentOptions(item.children, level + 1))
    }
  })
  return result
}

function handleAdd(parentId = 0) {
  dialogTitle.value = '添加分类'
  parentOptions.value = [{ label: '无上级分类', value: 0 }, ...extractParentOptions(cateList.value)]
  cateForm.value = { id: undefined, parentId, name: '', productUnit: '', sort: 0, navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' }
  dialogVisible.value = true
}

function handleEdit(row: any) {
  dialogTitle.value = '编辑分类'
  parentOptions.value = [{ label: '无上级分类', value: 0 }, ...extractParentOptions(cateList.value).filter((o: any) => o.value !== row.id)]
  cateForm.value = { ...row }
  dialogVisible.value = true
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
  await productCategoryDeleteByIdAPI(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleToggleNav(row: any) {
  const newStatus = row.navStatus === 1 ? 0 : 1
  await productCategoryUpdateNavStatusAPI({ ids: String(row.id), navStatus: newStatus })
  ElMessage.success('导航栏显示状态已更新')
  fetchData()
}

async function handleToggleShow(row: any) {
  const newStatus = row.showStatus === 1 ? 0 : 1
  await productCategoryUpdateShowStatusAPI({ ids: String(row.id), showStatus: newStatus })
  ElMessage.success('显示状态已更新')
  fetchData()
}

async function handleSaveCate() {
  if (!cateForm.value.name) return ElMessage.warning('请输入分类名称')
  if (cateForm.value.id) {
    await updateProductCategoryAPI(cateForm.value.id, cateForm.value as any)
    ElMessage.success('编辑成功')
  } else {
    await createProductCategoryAPI(cateForm.value as any)
    ElMessage.success('添加成功')
  }
  dialogVisible.value = false
  fetchData()
}
</script>

<template>
  <div class="page-cate-list">
    <el-card class="toolbar-card" shadow="never">
      <el-button type="primary" :icon="Plus" @click="handleAdd(0)">添加分类</el-button>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table v-loading="listLoading" :data="cateList" row-key="id" default-expand-all border style="width: 100%">
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="分类名称" prop="name" min-width="160">
          <template #default="{ row }">
            <el-icon style="margin-right: 4px; vertical-align: middle;"><component :is="row.icon || 'FolderOpened'" /></el-icon>
            <span>{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.level === 0" size="small" type="primary">一级</el-tag>
            <el-tag v-else size="small" type="success">二级</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品数量" prop="productCount" width="90" align="center" />
        <el-table-column label="数量单位" prop="productUnit" width="80" align="center" />
        <el-table-column label="导航栏" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.navStatus" :active-value="1" :inactive-value="0" @change="handleToggleNav(row)" />
          </template>
        </el-table-column>
        <el-table-column label="是否显示" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.showStatus" :active-value="1" :inactive-value="0" @change="handleToggleShow(row)" />
          </template>
        </el-table-column>
        <el-table-column label="排序" prop="sort" width="70" align="center" />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Plus" size="small" @click="handleAdd(row.id)">添加子类</el-button>
            <el-button link type="primary" :icon="Edit" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 分类表单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form :model="cateForm" label-width="100px">
        <el-form-item label="上级分类">
          <el-select v-model="cateForm.parentId" placeholder="选择上级分类" style="width: 100%">
            <el-option v-for="opt in parentOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类名称" required>
          <el-input v-model="cateForm.name" placeholder="分类名称" />
        </el-form-item>
        <el-form-item label="数量单位" required>
          <el-input v-model="cateForm.productUnit" placeholder="件 / 个 / 套" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="cateForm.sort" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否显示">
          <el-radio-group v-model="cateForm.showStatus">
            <el-radio :label="1">是</el-radio>
            <el-radio :label="0">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导航栏显示">
          <el-radio-group v-model="cateForm.navStatus">
            <el-radio :label="1">是</el-radio>
            <el-radio :label="0">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分类图标">
          <el-input v-model="cateForm.icon" placeholder="图标名称" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="cateForm.keywords" placeholder="关键词" />
        </el-form-item>
        <el-form-item label="分类描述">
          <el-input v-model="cateForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page-cate-list {
  .toolbar-card { margin-bottom: 12px; border-radius: 8px; }
  .table-card { border-radius: 8px; }
}
</style>
