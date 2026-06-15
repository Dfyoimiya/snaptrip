<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { getResourceCategoryListAllAPI, fetchAllResourceList, resourceCreateAPI, resourceUpdateByIdAPI, resourceDeleteByIdAPI } from '@/apis/resource'
import type { UmsResource, UmsResourceCategory } from '@/types/resource'

const listQuery = ref({ categoryId: undefined as number | undefined, nameKeyword: '', urlKeyword: '', pageNum: 1, pageSize: 10 })

const categoryOptions = ref<{ label: string; value: number }[]>([])
const allResources = ref<UmsResource[]>([])
const list = ref<UmsResource[]>([])
const total = ref(0)
const listLoading = ref(false)
const multipleSelection = ref<UmsResource[]>([])
const operateType = ref<number>()
const operateOptions = ref([{ label: '删除', value: 1 }])

const dialogVisible = ref(false)
const isEdit = ref(false)
const resource = ref<UmsResource>({ name: '', url: '', categoryId: 1, description: '' })

const fetchData = async () => {
  listLoading.value = true
  try {
    const [categories, resources] = await Promise.all([
      getResourceCategoryListAllAPI(),
      fetchAllResourceList(),
    ])
    categoryOptions.value = (categories.data || []).map((item: UmsResourceCategory) => ({ label: item.name || '', value: Number(item.id) || 0 }))
    allResources.value = resources.data || []
  } catch {
    allResources.value = []
  }
  applyFilters()
}

const applyFilters = () => {
  let result = [...allResources.value]
  if (listQuery.value.categoryId !== undefined) result = result.filter(item => item.categoryId === listQuery.value.categoryId)
  if (listQuery.value.nameKeyword) result = result.filter(item => item.name?.includes(listQuery.value.nameKeyword))
  if (listQuery.value.urlKeyword) result = result.filter(item => item.url?.includes(listQuery.value.urlKeyword))
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}

onMounted(() => { fetchData() })

const handleResetSearch = () => { listQuery.value = { categoryId: undefined, nameKeyword: '', urlKeyword: '', pageNum: 1, pageSize: 10 }; applyFilters() }
const handleSearchList = () => { listQuery.value.pageNum = 1; applyFilters() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; applyFilters() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; applyFilters() }
const handleSelectionChange = (val: UmsResource[]) => { multipleSelection.value = val }

const handleAdd = () => { dialogVisible.value = true; isEdit.value = false; resource.value = { name: '', url: '', categoryId: listQuery.value.categoryId || 1, description: '' } }
const handleUpdate = (_index: number, row: UmsResource) => { dialogVisible.value = true; isEdit.value = true; resource.value = { ...row } }
const handleDelete = async (_index: number, row: UmsResource) => {
  await ElMessageBox.confirm('是否要删除该资源?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  try {
    await resourceDeleteByIdAPI(row.id!)
    ElMessage.success('删除成功!')
    fetchData()
  } catch {
    ElMessage.error('删除失败')
  }
}

const handleDialogConfirm = async () => {
  try {
    if (isEdit.value) {
      await resourceUpdateByIdAPI(resource.value.id!, resource.value)
      ElMessage.success('修改成功！')
    } else {
      await resourceCreateAPI(resource.value)
      ElMessage.success('添加成功！')
    }
    dialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleBatchOperate = async () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) { ElMessage({ message: '请选择要操作的条目', type: 'warning', duration: 1000 }); return }
  if (operateType.value === 1) {
    await ElMessageBox.confirm('是否要进行删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    try {
      const ids = multipleSelection.value.map(item => item.id!)
      await Promise.all(ids.map(id => resourceDeleteByIdAPI(id)))
      ElMessage.success('删除成功！')
      fetchData()
    } catch {
      ElMessage.error('批量删除失败')
    }
  }
}

const getCategoryName = (categoryId?: number) => categoryOptions.value.find(item => item.value === categoryId)?.label || ''
</script>

<template>
  <div class="app-container">
    <el-card class="filter-container" shadow="never">
      <div>
        <el-icon class="el-icon-middle"><Search /></el-icon>
        <span>筛选搜索</span>
        <el-button style="float: right" @click="handleSearchList()" type="primary">查询搜索</el-button>
        <el-button style="float: right; margin-right: 15px" @click="handleResetSearch()">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="资源分类：">
            <el-select v-model="listQuery.categoryId" placeholder="全部" clearable class="input-width">
              <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="资源名称："><el-input v-model="listQuery.nameKeyword" class="input-width" placeholder="资源名称" clearable /></el-form-item>
          <el-form-item label="资源路径："><el-input v-model="listQuery.urlKeyword" class="input-width" placeholder="资源路径" clearable /></el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button class="btn-add" @click="handleAdd()">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="resourceTable" :data="list" style="width: 100%;" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center" />
        <el-table-column label="编号" width="80" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="资源名称" align="center"><template #default="scope">{{ scope.row.name }}</template></el-table-column>
        <el-table-column label="资源路径" align="center"><template #default="scope">{{ scope.row.url }}</template></el-table-column>
        <el-table-column label="资源分类" width="120" align="center"><template #default="scope">{{ getCategoryName(scope.row.categoryId) }}</template></el-table-column>
        <el-table-column label="描述" align="center"><template #default="scope">{{ scope.row.description }}</template></el-table-column>
        <el-table-column label="添加时间" width="180" align="center"><template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template></el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="handleUpdate(scope.$index, scope.row)">编辑</el-button>
            <el-button size="small" type="primary" link @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="batch-operate-container">
      <el-select v-model="operateType" placeholder="批量操作">
        <el-option v-for="item in operateOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button style="margin-left: 20px" class="search-button" @click="handleBatchOperate()" type="primary">确定</el-button>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>
    <el-dialog :title="isEdit ? '编辑资源' : '添加资源'" v-model="dialogVisible" width="40%">
      <el-form :model="resource" label-width="150px">
        <el-form-item label="资源名称："><el-input v-model="resource.name" style="width: 250px" /></el-form-item>
        <el-form-item label="资源路径："><el-input v-model="resource.url" style="width: 250px" /></el-form-item>
        <el-form-item label="资源分类：">
          <el-select v-model="resource.categoryId" placeholder="请选择" style="width: 250px">
            <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述："><el-input v-model="resource.description" type="textarea" :rows="5" style="width: 250px" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleDialogConfirm()">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.input-width { width: 203px; }
.batch-operate-container { display: inline-block; margin-top: 12px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
