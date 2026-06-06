<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()
const listQuery = ref({ pageNum: 1, pageSize: 10, keyword: '' })

const allList = ref([
  { id: 1, name: '超级管理员', description: '拥有所有权限', adminCount: 1, status: 1, createTime: '2024-01-01T00:00:00' },
  { id: 2, name: '商品管理员', description: '负责商品管理模块', adminCount: 2, status: 1, createTime: '2024-01-02T00:00:00' },
  { id: 3, name: '订单管理员', description: '负责订单管理模块', adminCount: 2, status: 1, createTime: '2024-01-03T00:00:00' },
  { id: 4, name: '会员管理员', description: '负责会员管理模块', adminCount: 2, status: 1, createTime: '2024-01-04T00:00:00' },
  { id: 5, name: '运营人员', description: '负责营销和内容管理', adminCount: 1, status: 1, createTime: '2024-01-05T00:00:00' },
  { id: 6, name: '客服人员', description: '负责客服和售后', adminCount: 2, status: 1, createTime: '2024-01-06T00:00:00' },
  { id: 7, name: '财务人员', description: '负责财务管理', adminCount: 1, status: 0, createTime: '2024-01-07T00:00:00' },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)
const role = ref<any>({ name: '', adminCount: 0, status: 1 })
const dialogVisible = ref(false)
const isEdit = ref(false)

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  if (listQuery.value.keyword) result = result.filter(item => item.name?.includes(listQuery.value.keyword))
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

const handleAdd = () => { dialogVisible.value = true; isEdit.value = false; role.value = { name: '', adminCount: 0, status: 1 } }
const handleUpdate = (_index: number, row: any) => { dialogVisible.value = true; isEdit.value = true; role.value = { ...row } }
const handleStatusChange = (_index: number, row: any) => { ElMessage.success('修改成功!') }
const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该角色?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => item.id !== row.id); getList(); ElMessage.success('删除成功!')
}
const handleDialogConfirm = () => {
  if (isEdit.value) {
    const idx = allList.value.findIndex(item => item.id === role.value.id)
    if (idx > -1) allList.value[idx] = { ...allList.value[idx], ...role.value }
    ElMessage.success('修改成功！')
  } else {
    allList.value.unshift({ ...role.value, id: Date.now(), createTime: new Date().toISOString() })
    ElMessage.success('添加成功！')
  }
  dialogVisible.value = false; getList()
}

const handleSelectMenu = (_index: number, row: any) => { router.push({ path: '/ums/allocMenu', query: { roleId: row.id } }) }
const handleSelectResource = (_index: number, row: any) => { router.push({ path: '/ums/allocResource', query: { roleId: row.id } }) }
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
        <el-table-column label="添加时间" width="160" align="center"><template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template></el-table-column>
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
