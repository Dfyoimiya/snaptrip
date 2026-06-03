<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const listQuery = ref({ categoryId: undefined as number | undefined, nameKeyword: '', urlKeyword: '', pageNum: 1, pageSize: 10 })

const categoryOptions = ref([
  { label: '商品模块', value: 1 },
  { label: '订单模块', value: 2 },
  { label: '会员模块', value: 3 },
  { label: '营销模块', value: 4 },
  { label: '权限模块', value: 5 },
])

const allList = ref([
  { id: 1, categoryId: 1, name: '商品列表查询', url: '/product/list', description: '查询商品列表', createTime: '2024-01-01T00:00:00' },
  { id: 2, categoryId: 1, name: '商品添加', url: '/product/create', description: '添加商品', createTime: '2024-01-02T00:00:00' },
  { id: 3, categoryId: 1, name: '商品修改', url: '/product/update', description: '修改商品', createTime: '2024-01-03T00:00:00' },
  { id: 4, categoryId: 1, name: '商品删除', url: '/product/delete', description: '删除商品', createTime: '2024-01-04T00:00:00' },
  { id: 5, categoryId: 2, name: '订单列表查询', url: '/order/list', description: '查询订单列表', createTime: '2024-01-05T00:00:00' },
  { id: 6, categoryId: 2, name: '订单关闭', url: '/order/close', description: '关闭订单', createTime: '2024-01-06T00:00:00' },
  { id: 7, categoryId: 2, name: '订单删除', url: '/order/delete', description: '删除订单', createTime: '2024-01-07T00:00:00' },
  { id: 8, categoryId: 3, name: '用户列表查询', url: '/admin/list', description: '查询用户列表', createTime: '2024-01-08T00:00:00' },
  { id: 9, categoryId: 3, name: '角色列表查询', url: '/role/list', description: '查询角色列表', createTime: '2024-01-09T00:00:00' },
  { id: 10, categoryId: 3, name: '菜单列表查询', url: '/menu/list', description: '查询菜单列表', createTime: '2024-01-10T00:00:00' },
  { id: 11, categoryId: 4, name: '优惠券查询', url: '/coupon/list', description: '查询优惠券', createTime: '2024-01-11T00:00:00' },
  { id: 12, categoryId: 4, name: '秒杀活动查询', url: '/flash/list', description: '查询秒杀活动', createTime: '2024-01-12T00:00:00' },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)
const multipleSelection = ref<any[]>([])
const operateType = ref<number>()
const operateOptions = ref([{ label: '删除', value: 1 }])

const dialogVisible = ref(false)
const isEdit = ref(false)
const resource = ref<any>({ name: '', url: '', categoryId: 1, description: '' })

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.categoryId !== undefined) result = result.filter(item => item.categoryId === listQuery.value.categoryId)
  if (listQuery.value.nameKeyword) result = result.filter(item => item.name?.includes(listQuery.value.nameKeyword))
  if (listQuery.value.urlKeyword) result = result.filter(item => item.url?.includes(listQuery.value.urlKeyword))
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}
onMounted(() => { getList() })

const handleResetSearch = () => { listQuery.value = { categoryId: undefined, nameKeyword: '', urlKeyword: '', pageNum: 1, pageSize: 10 }; getList() }
const handleSearchList = () => { listQuery.value.pageNum = 1; getList() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }
const handleSelectionChange = (val: any[]) => { multipleSelection.value = val }

const handleAdd = () => { dialogVisible.value = true; isEdit.value = false; resource.value = { name: '', url: '', categoryId: listQuery.value.categoryId || 1, description: '' } }
const handleUpdate = (_index: number, row: any) => { dialogVisible.value = true; isEdit.value = true; resource.value = { ...row } }
const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该资源?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => item.id !== row.id); getList(); ElMessage.success('删除成功!')
}

const handleDialogConfirm = () => {
  if (isEdit.value) {
    const idx = allList.value.findIndex(item => item.id === resource.value.id)
    if (idx > -1) allList.value[idx] = { ...allList.value[idx], ...resource.value }
    ElMessage.success('修改成功！')
  } else {
    allList.value.unshift({ ...resource.value, id: Date.now(), createTime: new Date().toISOString() })
    ElMessage.success('添加成功！')
  }
  dialogVisible.value = false; getList()
}

const handleBatchOperate = async () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) { ElMessage({ message: '请选择要操作的条目', type: 'warning', duration: 1000 }); return }
  if (operateType.value === 1) {
    await ElMessageBox.confirm('是否要进行删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const ids = multipleSelection.value.map(item => item.id)
    allList.value = allList.value.filter(item => !ids.includes(item.id)); getList(); ElMessage.success('删除成功！')
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
