<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import {
  getAdminListAPI,
  adminRegisterAPI,
  adminUpdateByIdAPI,
  adminUpdateStatusByIdAPI,
  adminDeleteByIdAPI,
  getRoleByAdminIdAPI,
  adminRoleUpdateAPI,
} from '@/apis/admin'
import { getRoleListAllAPI } from '@/apis/role'
import type { UmsAdmin } from '@/types/admin'
import type { UmsRole } from '@/types/role'
import type { PageParam } from '@/types/common'

const listQuery = ref({ pageNum: 1, pageSize: 10, keyword: '' })
const list = ref<UmsAdmin[]>([])
const total = ref(0)
const listLoading = ref(false)

const admin = ref<UmsAdmin>({ email: '', password: '', isActive: true })
const dialogVisible = ref(false)
const isEdit = ref(false)

const allocDialogVisible = ref(false)
const allocAdminId = ref<string>()
const allocRoleIds = ref<string[]>([])
const allRoleList = ref<UmsRole[]>([])

async function fetchData() {
  listLoading.value = true
  try {
    const params: PageParam = {
      keyword: listQuery.value.keyword || undefined,
      page: listQuery.value.pageNum,
      page_size: listQuery.value.pageSize,
    }
    const data = await getAdminListAPI(params)
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

const handleAdd = () => {
  dialogVisible.value = true
  isEdit.value = false
  admin.value = { email: '', password: '', isActive: true }
}
const handleUpdate = (_index: number, row: UmsAdmin) => { dialogVisible.value = true; isEdit.value = true; admin.value = { ...row } }
const handleStatusChange = async (_index: number, row: UmsAdmin) => {
  try {
    await adminUpdateStatusByIdAPI(row.id!, { status: row.isActive ? 1 : 0 })
    ElMessage.success('状态修改成功')
    fetchData()
  } catch (err: any) {
    ElMessage.error(err?.message || '状态修改失败')
    fetchData()
  }
}
const handleDelete = async (_index: number, row: UmsAdmin) => {
  try {
    await ElMessageBox.confirm('是否要删除该用户?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    await adminDeleteByIdAPI(row.id!)
    ElMessage.success('删除成功!')
    fetchData()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
  }
}
const handleDialogConfirm = async () => {
  try {
    if (isEdit.value) {
      await adminUpdateByIdAPI(admin.value.id!, admin.value)
      ElMessage.success('修改成功！')
    } else {
      await adminRegisterAPI(admin.value)
      ElMessage.success('添加成功！')
    }
    dialogVisible.value = false
    fetchData()
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
}

const handleSelectRole = async (_index: number, row: UmsAdmin) => {
  allocAdminId.value = row.id
  allocDialogVisible.value = true
  allocRoleIds.value = []
  try {
    const [roleData, adminRoleData] = await Promise.all([
      getRoleListAllAPI(),
      getRoleByAdminIdAPI(row.id!),
    ])
    allRoleList.value = roleData.data || []
    if (adminRoleData) {
      allocRoleIds.value = adminRoleData.data.map((r: any) => r.id)
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '获取角色信息失败')
  }
}
const handleAllocDialogConfirm = async () => {
  try {
    await adminRoleUpdateAPI({ adminId: allocAdminId.value!, roleIds: allocRoleIds.value })
    ElMessage.success('分配成功！')
    allocDialogVisible.value = false
  } catch (err: any) {
    ElMessage.error(err?.message || '分配失败')
  }
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
            <el-input v-model="listQuery.keyword" class="input-width" placeholder="帐号/姓名" clearable />
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button v-permission="'system:user'" class="btn-add" @click="handleAdd()">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="adminTable" :data="list" style="width: 100%;" v-loading="listLoading" border>
        <el-table-column label="编号" width="100" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="邮箱" align="center"><template #default="scope">{{ scope.row.email }}</template></el-table-column>
        <el-table-column label="添加时间" width="160" align="center"><template #default="scope">{{ formatDateTime(scope.row.createdAt) }}</template></el-table-column>
        <el-table-column label="是否启用" width="140" align="center">
          <template #default="scope"><el-switch v-model="scope.row.isActive" v-permission="'system:user'" @change="handleStatusChange(scope.$index, scope.row)" /></template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="scope">
            <el-button v-permission="'system:user'" size="small" type="primary" link @click="handleSelectRole(scope.$index, scope.row)">分配角色</el-button>
            <el-button v-permission="'system:user'" size="small" type="primary" link @click="handleUpdate(scope.$index, scope.row)">编辑</el-button>
            <el-button v-permission="'system:user'" size="small" type="danger" link @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '添加用户'" width="40%" :close-on-click-modal="false">
      <el-form :model="admin" label-width="150px">
        <el-form-item label="邮箱："><el-input v-model="admin.email" style="width: 250px" /></el-form-item>
        <el-form-item label="密码：" v-if="!isEdit"><el-input v-model="admin.password" type="password" style="width: 250px" /></el-form-item>
        <el-form-item label="是否启用：">
          <el-switch v-model="admin.isActive" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleDialogConfirm()">确 定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="分配角色" v-model="allocDialogVisible" width="30%">
      <el-select v-model="allocRoleIds" multiple placeholder="请选择" style="width: 80%">
        <el-option v-for="item in allRoleList" :key="item.id" :label="item.name" :value="item.id!" />
      </el-select>
      <template #footer>
        <el-button @click="allocDialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleAllocDialogConfirm()">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.input-width { width: 203px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
