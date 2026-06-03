<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Bottom, Top } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const listQuery = ref({ keyword: '' })
const list = ref([
  { id: 1, parentId: 0, title: '商品', name: 'pms', icon: 'Goods', level: 0, sort: 5, hidden: 0, createTime: '2024-01-01T00:00:00', children: [
    { id: 2, parentId: 1, title: '商品列表', name: 'product', icon: 'List', level: 1, sort: 4, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 3, parentId: 1, title: '添加商品', name: 'addProduct', icon: 'Plus', level: 1, sort: 3, hidden: 1, createTime: '2024-01-01T00:00:00' },
    { id: 4, parentId: 1, title: '商品分类', name: 'productCate', icon: 'FolderOpened', level: 1, sort: 2, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 5, parentId: 1, title: '商品类型', name: 'productAttr', icon: 'Collection', level: 1, sort: 1, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 13, parentId: 1, title: '品牌管理', name: 'brand', icon: 'Trophy', level: 1, sort: 0, hidden: 0, createTime: '2024-01-01T00:00:00' },
  ]},
  { id: 6, parentId: 0, title: '订单', name: 'oms', icon: 'Document', level: 0, sort: 4, hidden: 0, createTime: '2024-01-01T00:00:00', children: [
    { id: 7, parentId: 6, title: '订单列表', name: 'order', icon: 'List', level: 1, sort: 3, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 8, parentId: 6, title: '订单设置', name: 'orderSetting', icon: 'Setting', level: 1, sort: 2, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 9, parentId: 6, title: '退货申请', name: 'returnApply', icon: 'RefreshLeft', level: 1, sort: 1, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 14, parentId: 6, title: '退货原因', name: 'returnReason', icon: 'Warning', level: 1, sort: 0, hidden: 0, createTime: '2024-01-01T00:00:00' },
  ]},
  { id: 10, parentId: 0, title: '会员', name: 'ums', icon: 'User', level: 0, sort: 3, hidden: 0, createTime: '2024-01-01T00:00:00', children: [
    { id: 11, parentId: 10, title: '用户管理', name: 'admin', icon: 'UserFilled', level: 1, sort: 4, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 12, parentId: 10, title: '角色管理', name: 'role', icon: 'Medal', level: 1, sort: 3, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 15, parentId: 10, title: '菜单管理', name: 'menu', icon: 'Menu', level: 1, sort: 2, hidden: 0, createTime: '2024-01-01T00:00:00' },
    { id: 16, parentId: 10, title: '资源管理', name: 'resource', icon: 'Collection', level: 1, sort: 1, hidden: 0, createTime: '2024-01-01T00:00:00' },
  ]},
])
const listLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const menu = ref<any>({ parentId: 0, title: '', name: '', icon: '', sort: 0, hidden: 0 })
const parentOptions = ref([{ label: '无上级菜单', value: 0 }])

const levelFilter = (value: number) => value === 0 ? '一级' : value === 1 ? '二级' : '三级'
const disableNextLevel = (value: number) => value >= 2

const handleAdd = (row: any) => {
  dialogVisible.value = true; isEdit.value = false
  parentOptions.value = [{ label: '无上级菜单', value: 0 }]
  extractParentOptions(list.value, 0)
  menu.value = { parentId: row?.id || 0, title: '', name: '', icon: '', sort: 0, hidden: 0 }
}

const extractParentOptions = (items: any[], level: number) => {
  items.forEach(item => {
    parentOptions.value.push({ label: '  '.repeat(level) + item.title, value: item.id })
    if (item.children) extractParentOptions(item.children, level + 1)
  })
}

const handleEdit = (row: any) => {
  dialogVisible.value = true; isEdit.value = true
  parentOptions.value = [{ label: '无上级菜单', value: 0 }]
  extractParentOptions(list.value, 0)
  menu.value = { ...row }
}

const handleDelete = async (_index: number, row: any) => {
  await ElMessageBox.confirm('是否要删除该菜单?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  ElMessage({ message: '删除成功', type: 'success', duration: 1000 })
}

const handleHiddenChange = (_index: number, row: any) => {
  const label = row.hidden === 1 ? '隐藏' : '显示'
  ElMessage({ message: `已${label}`, type: 'success' })
}

const handleDialogConfirm = () => {
  dialogVisible.value = false; isEdit.value = false
  ElMessage({ message: isEdit.value ? '修改成功' : '添加成功', type: 'success', duration: 1000 })
}

const handleSearchList = () => {
  if (!listQuery.value.keyword) return
  // 简单过滤展示
  ElMessage({ message: '搜索完成', type: 'success', duration: 1000 })
}
const handleResetSearch = () => { listQuery.value.keyword = '' }
</script>

<template>
  <div class="app-container">
    <el-card class="filter-container" shadow="never">
      <div>
        <span>筛选搜索</span>
        <el-button style="float: right" @click="handleSearchList()" type="primary">查询搜索</el-button>
        <el-button style="float: right; margin-right: 15px" @click="handleResetSearch()">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="菜单名称："><el-input v-model="listQuery.keyword" class="input-width" placeholder="菜单名称" clearable /></el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card class="operate-container" shadow="never">
      <span>数据列表</span>
      <el-button class="btn-add" @click="handleAdd(null)">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table :data="list" style="width: 100%" row-key="id" v-loading="listLoading" border :tree-props="{ children: 'children', hasChildren: 'hasChildren' }">
        <el-table-column label="编号" width="100" align="center"><template #default="scope">{{ scope.row.id }}</template></el-table-column>
        <el-table-column label="菜单名称" align="center"><template #default="scope">{{ scope.row.title }}</template></el-table-column>
        <el-table-column label="菜单级数" width="100" align="center"><template #default="scope">{{ levelFilter(scope.row.level) }}</template></el-table-column>
        <el-table-column label="前端名称" align="center"><template #default="scope">{{ scope.row.name }}</template></el-table-column>
        <el-table-column label="前端图标" width="100" align="center"><template #default="scope"><el-icon><component :is="scope.row.icon || 'Document'" /></el-icon></template></el-table-column>
        <el-table-column label="是否显示" width="100" align="center">
          <template #default="scope"><el-switch @change="handleHiddenChange(scope.$index, scope.row)" :active-value="0" :inactive-value="1" v-model="scope.row.hidden" /></template>
        </el-table-column>
        <el-table-column label="排序" width="80" align="center"><template #default="scope">{{ scope.row.sort }}</template></el-table-column>
        <el-table-column label="设置" width="160" align="center">
          <template #default="scope"><el-button size="small" :icon="Plus" @click="handleAdd(scope.row)" :disabled="disableNextLevel(scope.row.level)">添加下级</el-button></template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" link :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="primary" link :icon="Delete" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog :title="isEdit ? '编辑菜单' : '添加菜单'" v-model="dialogVisible" width="40%">
      <el-form :model="menu" label-width="150px">
        <el-form-item label="上级菜单：">
          <el-select v-model="menu.parentId" placeholder="请选择菜单" style="width: 250px">
            <el-option v-for="item in parentOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="菜单名称："><el-input v-model="menu.title" style="width: 250px" /></el-form-item>
        <el-form-item label="前端名称："><el-input v-model="menu.name" style="width: 250px" /></el-form-item>
        <el-form-item label="前端图标："><el-input v-model="menu.icon" style="width: 250px" /></el-form-item>
        <el-form-item label="是否显示：">
          <el-radio-group v-model="menu.hidden"><el-radio :label="0">是</el-radio><el-radio :label="1">否</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item label="排序："><el-input v-model="menu.sort" style="width: 250px" /></el-form-item>
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
</style>
