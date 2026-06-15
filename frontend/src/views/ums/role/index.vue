<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import {
  getRoleListAPI,
  roleCreateAPI,
  roleUpdateByIdAPI,
  roleUpdateStatusAPI,
  roleDeleteByIdsAPI,
} from '@/apis/role'
import type { UmsRole } from '@/types/role'
import type { PageParam } from '@/types/common'

const router = useRouter()
const listQuery = ref({ pageNum: 1, pageSize: 10, keyword: '' })

const list = ref<UmsRole[]>([])
const total = ref(0)
const listLoading = ref(false)
const role = ref<UmsRole>({ name: '', adminCount: 0, status: 1 })
const dialogVisible = ref(false)
const isEdit = ref(false)

async function fetchData() {
  listLoading.value = true
  try {
    const params: PageParam = {
      keyword: listQuery.value.keyword || undefined,
      page: listQuery.value.pageNum,
      page_size: listQuery.value.pageSize,
    }
    const data = await getRoleListAPI(params)
    list.value = data.data.items || []
    total.value = data.data.total || 0
  } catch (err: any) {
    ElMessage.error(err?.message || '获取列表失败')
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchData() })

const handleResetSearch = () => { listQuery.value = { pageNum: 1, pageSize: 10, keyword: '' }; fetchData() }
const handleSearchList = () => { listQuery.value.pageNum = 1; fetchData() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; fetchData() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; fetchData() }

const handleAdd = () => { dialogVisible.value = true; isEdit.value = false; role.value = { name: '', adminCount: 0, status: 1 } }
const handleUpdate = (_index: number, row: UmsRole) => { dialogVisible.value = true; isEdit.value = true; role.value = { ...row } }
const handleStatusChange = async (_index: number, row: UmsRole) => {
  try {
    await roleUpdateStatusAPI(row.id!, { status: row.status! })
    ElMessage.success('修改成功!')
  } catch (err: any) {
    ElMessage.error(err?.message || '状态修改失败')
    fetchData()
  }
}
const handleDelete = async (_index: number, row: UmsRole) => {
  try {
    await ElMessageBox.confirm('是否要删除该角色?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    await roleDeleteByIdsAPI({ ids: String(row.id) })
    ElMessage.success('删除成功!')
    fetchData()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
  }
}
const handleDialogConfirm = async () => {
  try {
    if (isEdit.value) {
      await roleUpdateByIdAPI(role.value.id!, role.value as UmsRole)
      ElMessage.success('修改成功！')
    } else {
      await roleCreateAPI(role.value as UmsRole)
      ElMessage.success('添加成功！')
    }
    dialogVisible.value = false
    fetchData()
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
}

const handleSelectMenu = (_index: number, row: UmsRole) => {
  if (!row.id) return ElMessage.error('角色ID不能为空')
  router.push({ path: '/ums/allocMenu', query: { roleId: row.id, roleName: row.name } })
}
const handleSelectResource = (_index: number, row: UmsRole) => {
  if (!row.id) return ElMessage.error('角色ID不能为空')
  router.push({ path: '/ums/allocResource', query: { roleId: row.id, roleName: row.name } })
}
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
      <div style="margin-top: 15px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="输入搜索：">
            <el-input v-model="listQuery.keyword" class="input-width" placeholder="角色名称" clearable />
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button class="btn-add" @click="handleAdd()">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="roleTable" :data="list" style="width: 100%;" v-loading="listLoading" border>
        <el-table-column label="编号" width="100" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="角色名称" align="center"><template #default="scope">{{ scope.row.name }}</template></el-table-column>
        <el-table-column label="描述" align="center"><template #default="scope">{{ scope.row.description }}</template></el-table-column>
        <el-table-column label="用户数" width="100" align="center"><template #default="scope">{{ scope.row.adminCount }}</template></el-table-column>
        <el-table-column label="添加时间" width="160" align="center"><template #default="scope">{{ formatDateTime(scope.row.createdAt) }}</template></el-table-column>
        <el-table-column label="是否启用" width="140" align="center">
          <template #default="scope"><el-switch @change="handleStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="scope">
            <el-row>
              <el-col :span="12"><el-button size="small" type="primary" link @click="handleSelectMenu(scope.$index, scope.row)">分配菜单</el-button></el-col>
              <el-col :span="12"><el-button size="small" type="primary" link @click="handleSelectResource(scope.$index, scope.row)">分配资源</el-button></el-col>
            </el-row>
            <el-row>
              <el-col :span="12"><el-button size="small" type="primary" link @click="handleUpdate(scope.$index, scope.row)">编辑</el-button></el-col>
              <el-col :span="12"><el-button size="small" type="primary" link @click="handleDelete(scope.$index, scope.row)">删除</el-button></el-col>
            </el-row>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '添加角色'" width="40%">
      <el-form :model="role" label-width="150px">
        <el-form-item label="角色名称："><el-input v-model="role.name" style="width: 250px" /></el-form-item>
        <el-form-item label="描述："><el-input v-model="role.description" type="textarea" :rows="5" style="width: 250px" /></el-form-item>
        <el-form-item label="是否启用：">
          <el-radio-group v-model="role.status"><el-radio :label="1">是</el-radio><el-radio :label="0">否</el-radio></el-radio-group>
        </el-form-item>
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
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
