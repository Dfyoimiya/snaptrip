<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete, View } from '@element-plus/icons-vue'
import { getBrandListAPI, createBrandAPI, updateBrandAPI, brandDeleteByIdAPI, brandUpdateShowStatusAPI, brandUpdateFactoryStatusAPI } from '@/apis/brand'

// 搜索
const searchKeyword = ref('')
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const listLoading = ref(false)
const selectedRows = ref<any[]>([])

// 品牌数据
const brandList = ref<any[]>([])

async function fetchData() {
  listLoading.value = true
  try {
    const res = await getBrandListAPI({ keyword: searchKeyword.value, page: pageNum.value, page_size: pageSize.value })
    brandList.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchData() })

// 搜索
function handleSearch() {
  pageNum.value = 1
  fetchData()
}
function handleReset() {
  searchKeyword.value = ''
  pageNum.value = 1
  fetchData()
}
function handleSizeChange(val: number) { pageNum.value = 1; pageSize.value = val; fetchData() }
function handleCurrentChange(val: number) { pageNum.value = val; fetchData() }

// 添加/编辑
function handleAdd() {
  brandDialogTitle.value = '添加品牌'
  brandForm.value = { id: undefined, name: '', firstLetter: '', sort: 0, factoryStatus: 1, showStatus: 1, logo: '', bigPic: '', brandStory: '' }
  brandDialogVisible.value = true
}
function handleEdit(row: any) {
  brandDialogTitle.value = '编辑品牌'
  brandForm.value = { ...row }
  brandDialogVisible.value = true
}
async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除品牌「${row.name}」吗？`, '提示', { type: 'warning' })
  await brandDeleteByIdAPI(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

// 批量操作
async function handleBatchDelete() {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个品牌？`, '提示', { type: 'warning' })
  const ids = selectedRows.value.map((r: any) => r.id)
  for (const id of ids) {
    await brandDeleteByIdAPI(id)
  }
  ElMessage.success('批量删除成功')
  fetchData()
}
async function handleBatchShow(status: number) {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  for (const row of selectedRows.value) {
    await brandUpdateShowStatusAPI((row as any).id, status)
  }
  ElMessage.success(status === 1 ? '批量显示成功' : '批量隐藏成功')
  fetchData()
}
async function handleBatchFactory(status: number) {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  for (const row of selectedRows.value) {
    await brandUpdateFactoryStatusAPI((row as any).id, status)
  }
  ElMessage.success(status === 1 ? '批量设为制造商成功' : '批量取消制造商成功')
  fetchData()
}

function handleSelectionChange(val: any[]) { selectedRows.value = val }

// 品牌表单弹窗
const brandDialogVisible = ref(false)
const brandDialogTitle = ref('')
const brandForm = ref<{ id?: string; name: string; firstLetter: string; sort: number; factoryStatus: number; showStatus: number; logo: string; bigPic: string; brandStory: string }>({ id: undefined, name: '', firstLetter: '', sort: 0, factoryStatus: 1, showStatus: 1, logo: '', bigPic: '', brandStory: '' })

async function handleSaveBrand() {
  if (!brandForm.value.name) return ElMessage.warning('请输入品牌名称')
  if (brandForm.value.id) {
    await updateBrandAPI(brandForm.value.id!, brandForm.value as any)
    ElMessage.success('编辑成功')
  } else {
    await createBrandAPI(brandForm.value as any)
    ElMessage.success('添加成功')
  }
  brandDialogVisible.value = false
  fetchData()
}
</script>

<template>
  <div class="page-brand-list">
    <!-- 搜索 -->
    <el-card class="search-card" shadow="never">
      <el-form inline>
        <el-form-item label="品牌名称">
          <el-input v-model="searchKeyword" placeholder="输入品牌名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <el-button type="primary" :icon="Plus" @click="handleAdd">添加品牌</el-button>
          <el-dropdown split-button type="danger" @click="handleBatchDelete">
            批量删除
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleBatchShow(1)">批量显示</el-dropdown-item>
                <el-dropdown-item @click="handleBatchShow(0)">批量隐藏</el-dropdown-item>
                <el-dropdown-item @click="handleBatchFactory(1)">批量设为制造商</el-dropdown-item>
                <el-dropdown-item @click="handleBatchFactory(0)">批量取消制造商</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>

      <el-table v-loading="listLoading" :data="brandList" style="width: 100%" @selection-change="handleSelectionChange" border>
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="60" align="center" />
        <el-table-column label="品牌Logo" width="90" align="center">
          <template #default="{ row }">
            <el-image v-if="row.logo" :src="row.logo" style="width: 50px; height: 50px; border-radius: 4px;" fit="cover" />
            <div v-else class="logo-placeholder">{{ row.name.charAt(0) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="品牌名称" prop="name" min-width="120" />
        <el-table-column label="首字母" prop="firstLetter" width="70" align="center" />
        <el-table-column label="排序" prop="sort" width="60" align="center" />
        <el-table-column label="制造商" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.factoryStatus" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="显示" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.showStatus" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="商品数量" prop="productCount" width="90" align="center" />
        <el-table-column label="评论数" prop="productCommentCount" width="80" align="center" />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pageNum" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="handleSizeChange" @current-change="handleCurrentChange" />
      </div>
    </el-card>

    <!-- 品牌弹窗 -->
    <el-dialog v-model="brandDialogVisible" :title="brandDialogTitle" width="600px" destroy-on-close>
      <el-form :model="brandForm" label-width="100px">
        <el-row :gutter="20">
          <el-col :xs="24" :lg="12">
            <el-form-item label="品牌名称" required>
              <el-input v-model="brandForm.name" placeholder="品牌名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="首字母">
              <el-input v-model="brandForm.firstLetter" placeholder="A-Z" maxlength="1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="排序">
              <el-input-number v-model="brandForm.sort" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="是否为制造商">
              <el-radio-group v-model="brandForm.factoryStatus">
                <el-radio :value="1">是</el-radio>
                <el-radio :value="0">否</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="是否显示">
              <el-radio-group v-model="brandForm.showStatus">
                <el-radio :value="1">是</el-radio>
                <el-radio :value="0">否</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="Logo链接">
              <el-input v-model="brandForm.logo" placeholder="Logo图片URL" />
            </el-form-item>
          </el-col>
          <el-col :xs="24">
            <el-form-item label="品牌故事">
              <el-input v-model="brandForm.brandStory" type="textarea" :rows="4" placeholder="品牌故事介绍" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="brandDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveBrand">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page-brand-list {
  .search-card { margin-bottom: 12px; border-radius: 8px; }
  .table-card { border-radius: 8px; }
  .table-header { display: flex; gap: 10px; }
  .pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
  .logo-placeholder {
    width: 50px; height: 50px; border-radius: 4px;
    background: linear-gradient(135deg, #165dff, #36cfc9);
    color: #fff; font-size: 20px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto;
  }
}
</style>
