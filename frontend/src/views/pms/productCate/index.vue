<script lang="ts" setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Rank } from '@element-plus/icons-vue'
import Sortable, { type SortableEvent } from 'sortablejs'
import {
  getProductCategoryListWithChildrenAPI,
  createProductCategoryAPI,
  updateProductCategoryAPI,
  productCategoryDeleteByIdAPI,
  productCategoryUpdateNavStatusAPI,
  productCategoryUpdateShowStatusAPI,
  productCategoryBatchSortAPI,
} from '@/apis/productCate'

// 分类数据（树形）
const cateList = ref<any[]>([])
const listLoading = ref(false)

async function fetchData() {
  listLoading.value = true
  try {
    const res = await getProductCategoryListWithChildrenAPI()
    cateList.value = res.data || []
    await nextTick()
    initSortable()
  } finally {
    listLoading.value = false
  }
}
onMounted(() => { fetchData() })

// ── 拖拽排序 ──
const tableRef = ref<any>(null)
let sortableInstance: Sortable | null = null

function flattenTree(list: any[]): any[] {
  const result: any[] = []
  function walk(items: any[]) {
    items.forEach(item => {
      result.push(item)
      if (item.children?.length) walk(item.children)
    })
  }
  walk(list)
  return result
}

function initSortable() {
  const el = document.querySelector('.sortable-table .el-table__body-wrapper tbody')
  if (!el) return
  if (sortableInstance) sortableInstance.destroy()

  sortableInstance = Sortable.create(el as HTMLElement, {
    handle: '.drag-handle',
    animation: 200,
    easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    ghostClass: 'sortable-ghost',
    dragClass: 'sortable-drag',
    onEnd: async (evt: SortableEvent) => {
      const { oldIndex, newIndex, item: evtItem } = evt
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return
      if (!evtItem) return

      // Identify the dragged category by row-key
      const draggedId = (evtItem as HTMLElement).getAttribute('data-row-key')
      if (!draggedId) return

      // Find the item in the tree to get its parentId
      const flat = flattenTree(cateList.value)
      const draggedItem = flat.find((item: any) => String(item.id) === draggedId)
      if (!draggedItem) return
      const parentId = draggedItem.parentId ?? null

      // Find sibling group in tree
      function findSiblingGroup(items: any[], targetParentId: any): any[] | null {
        for (const item of items) {
          if (item.id === targetParentId) return item.children || []
          if (item.children?.length) {
            const found = findSiblingGroup(item.children, targetParentId)
            if (found !== null) return found
          }
        }
        return null
      }

      const topLevelSiblings = cateList.value.filter((item: any) => (item.parentId ?? null) === parentId)
      const group = parentId ? findSiblingGroup(cateList.value, parentId) || topLevelSiblings : topLevelSiblings

      // Renumber sort sequentially within the group
      const reorderItems: { id: string; sort: number }[] = group.map((item: any, idx: number) => {
        item.sort = idx
        return { id: item.id, sort: idx }
      })

      try {
        await productCategoryBatchSortAPI({ items: reorderItems })
        ElMessage.success('排序已更新')
      } catch {
        ElMessage.error('排序更新失败')
        fetchData()
      }
    },
  })
}

// ── 弹窗 ──
const dialogVisible = ref(false)
const dialogTitle = ref('')
const cateForm = ref<{
  id?: string; parentId: number; name: string; productUnit: string;
  navStatus: number; showStatus: number; icon: string; keywords: string; description: string
}>({ id: undefined, parentId: 0, name: '', productUnit: '', navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' })
const parentOptions = ref([{ label: '无上级分类', value: 0 }])

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
  cateForm.value = { id: undefined, parentId, name: '', productUnit: '', navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' }
  dialogVisible.value = true
}

function handleEdit(row: any) {
  dialogTitle.value = '编辑分类'
  parentOptions.value = [{ label: '无上级分类', value: 0 }, ...extractParentOptions(cateList.value).filter((o: any) => o.value !== row.id)]
  cateForm.value = { ...row, parentId: row.parentId ?? 0 }
  dialogVisible.value = true
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
  await productCategoryDeleteByIdAPI(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleToggleNav(row: any, newVal: number) {
  try {
    await productCategoryUpdateNavStatusAPI(String(row.id), newVal)
    ElMessage.success('导航栏显示状态已更新')
    fetchData()
  } catch {
    row.navStatus = newVal === 1 ? 0 : 1
  }
}

async function handleToggleShow(row: any, newVal: number) {
  try {
    await productCategoryUpdateShowStatusAPI(String(row.id), newVal)
    ElMessage.success('显示状态已更新')
    fetchData()
  } catch {
    row.showStatus = newVal === 1 ? 0 : 1
  }
}

async function handleSaveCate() {
  if (!cateForm.value.name) return ElMessage.warning('请输入分类名称')
  if (cateForm.value.id) {
    await updateProductCategoryAPI(cateForm.value.id, cateForm.value as any)
    ElMessage.success('编辑成功')
  } else {
    await createProductCategoryAPI(cateForm.value as any)
    ElMessage.success('添加成功')
  }
  dialogVisible.value = false
  fetchData()
}
</script>

<template>
  <div class="page-cate-list">
    <el-card class="toolbar-card" shadow="never">
      <el-button type="primary" :icon="Plus" @click="handleAdd(0)">添加分类</el-button>
      <span class="drag-tip">
        <el-icon><Rank /></el-icon>
        拖拽行前图标调整排序
      </span>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table
        ref="tableRef"
        v-loading="listLoading"
        :data="cateList"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
        border
        class="sortable-table"
        style="width: 100%"
      >
        <el-table-column label="" width="64" align="center" class-name="drag-col">
          <template #default>
            <el-icon class="drag-handle" :size="20">
              <Rank />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="分类名称" prop="name" min-width="220">
          <template #default="{ row }">
            <span :style="{ paddingLeft: row.level * 24 + 'px' }">
              <el-icon style="margin-right: 4px; vertical-align: middle;">
                <component :is="(row.icon && /^[A-Z][A-Za-z0-9]+$/.test(row.icon)) ? row.icon : (row.children && row.children.length ? 'FolderOpened' : 'Document')" />
              </el-icon>
              <span>{{ row.name }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.level === 0" size="small" type="primary">一级</el-tag>
            <el-tag v-else-if="row.level === 1" size="small" type="success">二级</el-tag>
            <el-tag v-else size="small" type="warning">三级</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品数" prop="productCount" width="80" align="center" />
        <el-table-column label="单位" prop="productUnit" width="70" align="center" />
        <el-table-column label="排序" prop="sort" width="80" align="center" />
        <el-table-column label="导航栏" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.navStatus" :active-value="1" :inactive-value="0" @change="(val: any) => handleToggleNav(row, Number(val))" />
          </template>
        </el-table-column>
        <el-table-column label="显示" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.showStatus" :active-value="1" :inactive-value="0" @change="(val: any) => handleToggleShow(row, Number(val))" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.level < 2" link type="primary" :icon="Plus" size="small" @click="handleAdd(row.id)">添加子类</el-button>
            <el-button v-else link type="info" size="small" disabled>已达上限</el-button>
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
        <el-form-item label="是否显示">
          <el-radio-group v-model="cateForm.showStatus">
            <el-radio :value="1">是</el-radio>
            <el-radio :value="0">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导航栏显示">
          <el-radio-group v-model="cateForm.navStatus">
            <el-radio :value="1">是</el-radio>
            <el-radio :value="0">否</el-radio>
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
  .toolbar-card {
    margin-bottom: 12px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 16px;
    .drag-tip {
      color: #909399;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
  .table-card { border-radius: 8px; }
}
</style>

<style lang="scss">
// 拖拽样式必须全局 —— SortableJS 直接操作 DOM，不受 Vue scoped 影响
.sortable-ghost {
  opacity: 0.4;
  background: #e6f7ff !important;
}
.sortable-drag {
  background: #fff !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

// 拖拽列不使用 Element Plus 默认的文本省略规则，避免图标被显示成 "..."
.sortable-table {
  th.drag-col,
  td.drag-col {
    padding: 0;

    .cell {
      display: flex;
      width: 100%;
      height: 100%;
      min-height: 48px;
      align-items: center;
      justify-content: center;
      overflow: visible;
      padding: 0;
      text-overflow: clip;
      white-space: normal;
    }
  }

  .drag-handle {
    display: inline-flex;
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    align-items: center;
    justify-content: center;
    cursor: grab;
    border-radius: 6px;
    color: #909399;
    transition: color 0.15s ease, background-color 0.15s ease;

    &:hover {
      color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
    }

    &:active {
      cursor: grabbing;
    }
  }
}
</style>
