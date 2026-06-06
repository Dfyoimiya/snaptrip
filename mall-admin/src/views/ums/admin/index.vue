<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const listQuery = ref({ pageNum: 1, pageSize: 10, keyword: '' })
const allList = ref([
  { id: 1, username: 'admin', nickName: '系统管理员', email: 'admin@mall.com', createTime: '2024-01-01T00:00:00', loginTime: '2024-05-28T10:30:00', status: 1 },
  { id: 2, username: 'macro', nickName: '宏哥', email: 'macro@mall.com', createTime: '2024-01-15T00:00:00', loginTime: '2024-05-27T14:20:00', status: 1 },
  { id: 3, username: 'test01', nickName: '测试员01', email: 'test01@mall.com', createTime: '2024-02-01T00:00:00', loginTime: '2024-05-26T09:10:00', status: 1 },
  { id: 4, username: 'test02', nickName: '测试员02', email: 'test02@mall.com', createTime: '2024-02-15T00:00:00', loginTime: '2024-05-25T16:45:00', status: 0 },
  { id: 5, username: 'operator', nickName: '运营人员', email: 'op@mall.com', createTime: '2024-03-01T00:00:00', loginTime: '2024-05-24T11:30:00', status: 1 },
  { id: 6, username: 'cs01', nickName: '客服01', email: 'cs01@mall.com', createTime: '2024-03-15T00:00:00', loginTime: '2024-05-23T20:00:00', status: 1 },
  { id: 7, username: 'cs02', nickName: '客服02', email: 'cs02@mall.com', createTime: '2024-04-01T00:00:00', loginTime: '2024-05-22T08:15:00', status: 1 },
  { id: 8, username: 'finance', nickName: '财务人员', email: 'finance@mall.com', createTime: '2024-04-15T00:00:00', loginTime: '2024-05-21T13:40:00', status: 0 },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)

const admin = ref<any>({ username: '', password: '', status: 1 })
const dialogVisible = ref(false)
const isEdit = ref(false)

const allocDialogVisible = ref(false)
const allocAdminId = ref<number>()
const allocRoleIds = ref<number[]>([])
const allRoleList = ref([
  { id: 1, name: '超级管理员' },
  { id: 2, name: '商品管理员' },
  { id: 3, name: '订单管理员' },
  { id: 4, name: '会员管理员' },
  { id: 5, name: '运营人员' },
  { id: 6, name: '客服人员' },
  { id: 7, name: '财务人员' },
])

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.keyword) result = result.filter(item => item.username?.includes(listQuery.value.keyword) || item.nickName?.includes(listQuery.value.keyword))
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}
onMounted(() => { getList() })

const handleResetSearch = () => { listQuery.value = { pageNum: 1, pageSize: 10, keyword: '' }; getList() }
const handleSearchList = () => { listQuery.value.pageNum = 1; getList() }
const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }

const handleAdd = () => { dialogVisible.value = true; isEdit.value = false; admin.value = { username: '', password: '', status: 1 } }
const handleUpdate = (_index: number, row: any) => { dialogVisible.value = true; isEdit.value = true; admin.value = Object.assign({}, row) }
const handleStatusChange = (_index: number, row: any) => { ElMessage.success('状态修改成功') }
const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该用户?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => item.id !== row.id); getList(); ElMessage.success('删除成功!')
}
const handleDialogConfirm = () => {
  if (isEdit.value) {
    const idx = allList.value.findIndex(item => item.id === admin.value.id)
    if (idx > -1) allList.value[idx] = { ...allList.value[idx], ...admin.value }
    ElMessage.success('修改成功！')
  } else {
    allList.value.unshift({ ...admin.value, id: Date.now(), createTime: new Date().toISOString() })
    ElMessage.success('添加成功！')
  }
  dialogVisible.value = false; getList()
}

const handleSelectRole = (_index: number, row: any) => { allocAdminId.value = row.id; allocDialogVisible.value = true; allocRoleIds.value = [] }
const handleAllocDialogConfirm = () => { ElMessage.success('分配成功！'); allocDialogVisible.value = false }
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
      <el-button class="btn-add" @click="handleAdd()">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="adminTable" :data="list" style="width: 100%;" v-loading="listLoading" border>
        <el-table-column label="编号" width="100" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="帐号" align="center"><template #default="scope">{{ scope.row.username }}</template></el-table-column>
        <el-table-column label="姓名" align="center"><template #default="scope">{{ scope.row.nickName }}</template></el-table-column>
        <el-table-column label="邮箱" align="center"><template #default="scope">{{ scope.row.email }}</template></el-table-column>
        <el-table-column label="添加时间" width="160" align="center"><template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template></el-table-column>
        <el-table-column label="最后登录" width="160" align="center"><template #default="scope">{{ formatDateTime(scope.row.loginTime) }}</template></el-table-column>
        <el-table-column label="是否启用" width="140" align="center">
          <template #default="scope"><el-switch @change="handleStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="handleSelectRole(scope.$index, scope.row)">分配角色</el-button>
            <el-button size="small" type="primary" link @click="handleUpdate(scope.$index, scope.row)">编辑</el-button>
            <el-button size="small" type="primary" link @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '添加用户'" width="40%">
      <el-form :model="admin" label-width="150px">
        <el-form-item label="帐号："><el-input v-model="admin.username" style="width: 250px" /></el-form-item>
        <el-form-item label="姓名："><el-input v-model="admin.nickName" style="width: 250px" /></el-form-item>
        <el-form-item label="邮箱："><el-input v-model="admin.email" style="width: 250px" /></el-form-item>
        <el-form-item label="密码：" v-if="!isEdit"><el-input v-model="admin.password" type="password" style="width: 250px" /></el-form-item>
        <el-form-item label="备注："><el-input v-model="admin.note" type="textarea" :rows="5" style="width: 250px" /></el-form-item>
        <el-form-item label="是否启用：">
          <el-radio-group v-model="admin.status"><el-radio :label="1">是</el-radio><el-radio :label="0">否</el-radio></el-radio-group>
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
