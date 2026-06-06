<script lang="ts" setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Bottom, Top, View } from '@element-plus/icons-vue'

// 分类数据（树形）
const cateList = ref([
  {
    id: 1, parentId: 0, name: '手机数码', level: 0, productCount: 156, productUnit: '件', navStatus: 1, showStatus: 1, sort: 100, icon: 'Phone', keywords: '手机', description: '手机、平板等数码产品',
    children: [
      { id: 11, parentId: 1, name: '手机', level: 1, productCount: 86, productUnit: '部', navStatus: 1, showStatus: 1, sort: 99, icon: 'Cellphone', keywords: '智能手机', description: '各品牌智能手机', children: [] },
      { id: 12, parentId: 1, name: '平板电脑', level: 1, productCount: 32, productUnit: '台', navStatus: 1, showStatus: 1, sort: 98, icon: 'Monitor', keywords: '平板电脑', description: 'iPad及安卓平板', children: [] },
      { id: 13, parentId: 1, name: '智能手表', level: 1, productCount: 38, productUnit: '只', navStatus: 1, showStatus: 1, sort: 97, icon: 'Clock', keywords: '智能手表手环', description: '智能穿戴设备', children: [] },
    ],
  },
  {
    id: 2, parentId: 0, name: '电脑办公', level: 0, productCount: 98, productUnit: '件', navStatus: 1, showStatus: 1, sort: 95, icon: 'Monitor', keywords: '电脑', description: '笔记本、台式机等',
    children: [
      { id: 21, parentId: 2, name: '笔记本电脑', level: 1, productCount: 45, productUnit: '台', navStatus: 1, showStatus: 1, sort: 94, icon: 'Notebook', keywords: '笔记本', description: '轻薄本、游戏本', children: [] },
      { id: 22, parentId: 2, name: '显示器', level: 1, productCount: 28, productUnit: '台', navStatus: 1, showStatus: 1, sort: 93, icon: 'FullScreen', keywords: '显示器', description: '各种尺寸显示器', children: [] },
    ],
  },
  {
    id: 3, parentId: 0, name: '服装鞋包', level: 0, productCount: 234, productUnit: '件', navStatus: 1, showStatus: 1, sort: 90, icon: 'Handbag', keywords: '服装', description: '男装女装鞋靴箱包',
    children: [
      { id: 31, parentId: 3, name: '男装', level: 1, productCount: 78, productUnit: '件', navStatus: 1, showStatus: 1, sort: 89, icon: 'User', keywords: '男装', description: '男士服装', children: [] },
      { id: 32, parentId: 3, name: '女装', level: 1, productCount: 92, productUnit: '件', navStatus: 1, showStatus: 1, sort: 88, icon: 'Female', keywords: '女装', description: '女士服装', children: [] },
      { id: 33, parentId: 3, name: '运动鞋', level: 1, productCount: 64, productUnit: '双', navStatus: 1, showStatus: 1, sort: 87, icon: 'Basketball', keywords: '运动鞋', description: '各品牌运动鞋', children: [] },
    ],
  },
])

const listLoading = ref(false)
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

function handleDelete(row: any) {
  ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' }).then(() => {
    cateList.value = cateList.value.filter(c => c.id !== row.id).map(c => {
      if (c.children) c.children = c.children.filter((child: any) => child.id !== row.id)
      return c
    })
    ElMessage.success('删除成功')
  })
}

function handleToggleNav(row: any) {
  row.navStatus = row.navStatus === 1 ? 0 : 1
  ElMessage.success('导航栏显示状态已更新')
}

function handleToggleShow(row: any) {
  row.showStatus = row.showStatus === 1 ? 0 : 1
  ElMessage.success('显示状态已更新')
}

function handleSaveCate() {
  if (!cateForm.value.name) return ElMessage.warning('请输入分类名称')
  if (cateForm.value.id) {
    // edit
    ElMessage.success('编辑成功')
  } else {
    // add
    const newId = Date.now()
    if (cateForm.value.parentId === 0) {
      cateList.value.push({ ...cateForm.value, id: newId, level: 0, productCount: 0, children: [] })
    } else {
      cateList.value.forEach(c => {
        if (c.id === cateForm.value.parentId) {
          if (!c.children) c.children = []
          c.children.push({ ...cateForm.value, id: newId, level: 1, productCount: 0, children: [] })
        }
      })
    }
    ElMessage.success('添加成功')
  }
  dialogVisible.value = false
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
