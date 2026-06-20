<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Bottom, Top } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import {
  getMenuTreeListAPI,
  menuCreateAPI,
  menuUpdateByIdAPI,
  menuDeleteByIdAPI,
  menuUpdateHiddenByIdAPI,
} from '@/apis/menu'
import type { UmsMenuNode, UmsMenu } from '@/types/menu'

const listQuery = ref({ keyword: '' })
const list = ref<UmsMenuNode[]>([])
const listLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const menu = ref<UmsMenu>({ parentId: '0', title: '', name: '', icon: '', sort: 0, hidden: 0 })
const parentOptions = ref([{ label: '无上级菜单', value: 0 }])

async function fetchList() {
  listLoading.value = true
  try {
    const data = await getMenuTreeListAPI()
    list.value = data.data || []
  } catch (err: any) {
    ElMessage.error(err?.message || '获取菜单列表失败')
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchList() })

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

const handleEdit = (row: UmsMenu) => {
  dialogVisible.value = true; isEdit.value = true
  parentOptions.value = [{ label: '无上级菜单', value: 0 }]
  extractParentOptions(list.value, 0)
  menu.value = { ...row }
}

const handleDelete = async (_index: number, row: UmsMenu) => {
  try {
    await ElMessageBox.confirm('是否要删除该菜单?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    await menuDeleteByIdAPI(row.id!)
    ElMessage({ message: '删除成功', type: 'success', duration: 1000 })
    fetchList()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
  }
}

const handleHiddenChange = async (_index: number, row: UmsMenu) => {
  try {
    await menuUpdateHiddenByIdAPI(row.id!, { hidden: row.hidden! })
    const label = row.hidden === 1 ? '隐藏' : '显示'
    ElMessage({ message: `已${label}`, type: 'success' })
    fetchList()
  } catch (err: any) {
    ElMessage.error(err?.message || '状态更新失败')
    fetchList()
  }
}

const handleDialogConfirm = async () => {
  try {
    const wasEdit = isEdit.value
    if (wasEdit) {
      await menuUpdateByIdAPI(menu.value.id!, menu.value as UmsMenu)
    } else {
      await menuCreateAPI(menu.value as UmsMenu)
    }
    dialogVisible.value = false
    isEdit.value = false
    ElMessage({ message: wasEdit ? '修改成功' : '添加成功', type: 'success', duration: 1000 })
    fetchList()
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
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
