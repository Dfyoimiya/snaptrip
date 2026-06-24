<script lang="ts" setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Rank } from '@element-plus/icons-vue'
import Sortable, { type MoveEvent, type SortableEvent } from 'sortablejs'
import {
  getProductCategoryListWithChildrenAPI,
  createProductCategoryAPI,
  updateProductCategoryAPI,
  productCategoryDeleteByIdAPI,
  productCategoryUpdateNavStatusAPI,
  productCategoryUpdateShowStatusAPI,
  productCategoryBatchSortAPI,
  productCategoryMoveAPI,
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
let lastMoveTargetParentId: string | null = null

type CategoryRow = {
  id: string | number
  parentId?: string | number | null
  name: string
  level?: number
  children?: CategoryRow[]
}

type FlatCategoryRow = {
  id: string
  parentId: string
  row: CategoryRow
}

function normalizeParentKey(parentId: string | number | null | undefined) {
  return parentId === null || parentId === undefined || parentId === 0 || parentId === '0'
    ? 'root'
    : String(parentId)
}

function flattenTree(list: CategoryRow[]): CategoryRow[] {
  const result: CategoryRow[] = []
  function walk(items: CategoryRow[]) {
    items.forEach(item => {
      result.push(item)
      if (item.children?.length) walk(item.children)
    })
  }
  walk(list)
  return result
}

function flattenVisibleTree(list: CategoryRow[]): FlatCategoryRow[] {
  const result: FlatCategoryRow[] = []
  function walk(items: CategoryRow[]) {
    items.forEach(item => {
      result.push({
        id: String(item.id),
        parentId: normalizeParentKey(item.parentId),
        row: item,
      })
      if (item.children?.length) walk(item.children)
    })
  }
  walk(list)
  return result
}

function findCategory(id: string | number | null | undefined) {
  if (id === null || id === undefined) return undefined
  return flattenTree(cateList.value).find((item: CategoryRow) => String(item.id) === String(id))
}

function collectDescendantIds(row: CategoryRow): Set<string> {
  const ids = new Set<string>()
  function walk(item: CategoryRow) {
    for (const child of item.children || []) {
      ids.add(String(child.id))
      walk(child)
    }
  }
  walk(row)
  return ids
}

function findSiblingGroup(items: CategoryRow[], targetParentId: string | number | null | undefined): CategoryRow[] {
  if (normalizeParentKey(targetParentId) === 'root') {
    return items
  }
  for (const item of items) {
    if (String(item.id) === String(targetParentId)) return item.children || []
    if (item.children?.length) {
      const found = findSiblingGroup(item.children, targetParentId)
      if (found.length) return found
    }
  }
  return []
}

function visibleRowIds(): string[] {
  return Array.from(document.querySelectorAll('.sortable-table .el-table__body-wrapper tbody tr'))
    .map(row => row.getAttribute('data-row-key'))
    .filter((id): id is string => Boolean(id))
}

function entryMapFromList(list: FlatCategoryRow[]) {
  return new Map(list.map(item => [item.id, item]))
}

function resolveChildBlockParent(row: CategoryRow | undefined) {
  if (!row || normalizeParentKey(row.parentId) === 'root') return undefined
  return findCategory(row.parentId)
}

function findHoverMoveParent(draggedItem: CategoryRow, targetParentId: string | null) {
  if (!targetParentId) return undefined
  const draggedParentId = normalizeParentKey(draggedItem.parentId)
  if (targetParentId === draggedParentId || targetParentId === String(draggedItem.id)) return undefined
  return findCategory(targetParentId)
}

function findBoundaryMoveParent(
  draggedItem: CategoryRow,
  idsAfterDrop: string[],
  originalEntries: FlatCategoryRow[],
) {
  const draggedId = String(draggedItem.id)
  const draggedParentId = normalizeParentKey(draggedItem.parentId)
  const draggedIndex = idsAfterDrop.indexOf(draggedId)
  if (draggedIndex < 0) return undefined

  const entryMap = entryMapFromList(originalEntries)
  const beforeEntry = idsAfterDrop
    .slice(0, draggedIndex)
    .reverse()
    .map(id => entryMap.get(id))
    .find((entry): entry is FlatCategoryRow => Boolean(entry))
  const afterEntry = idsAfterDrop
    .slice(draggedIndex + 1)
    .map(id => entryMap.get(id))
    .find((entry): entry is FlatCategoryRow => Boolean(entry))

  const candidateParentIds = [beforeEntry?.parentId, afterEntry?.parentId]
    .filter((parentId): parentId is string => Boolean(parentId && parentId !== 'root'))
  const sameChildBlockParentId = candidateParentIds.find(parentId => {
    const beforeInBlock = !beforeEntry || beforeEntry.parentId === parentId || beforeEntry.id === parentId
    const afterInBlock = !afterEntry || afterEntry.parentId === parentId || afterEntry.id === parentId
    return beforeInBlock && afterInBlock
  })

  if (!sameChildBlockParentId || sameChildBlockParentId === draggedParentId) return undefined
  return findCategory(sameChildBlockParentId)
}

function getMoveTargetParentId(evt: MoveEvent) {
  const draggedId = evt.dragged?.getAttribute('data-row-key')
  const relatedId = evt.related?.getAttribute('data-row-key')
  if (!draggedId || !relatedId || draggedId === relatedId) return null

  const draggedItem = findCategory(draggedId)
  const relatedItem = findCategory(relatedId)
  const candidateParent = resolveChildBlockParent(relatedItem)
  if (!draggedItem || !candidateParent || String(candidateParent.id) === draggedId) return null
  if (normalizeParentKey(draggedItem.parentId) === String(candidateParent.id)) return null
  if (collectDescendantIds(draggedItem).has(String(candidateParent.id))) return null
  return String(candidateParent.id)
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
    onStart: () => {
      lastMoveTargetParentId = null
    },
    onMove: (evt: MoveEvent) => {
      lastMoveTargetParentId = getMoveTargetParentId(evt)
      return true
    },
    onEnd: async (evt: SortableEvent) => {
      const { oldIndex, newIndex, item: evtItem } = evt
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return
      if (!evtItem) return

      const draggedId = (evtItem as HTMLElement).getAttribute('data-row-key')
      if (!draggedId) return

      const flat = flattenTree(cateList.value)
      const originalEntries = flattenVisibleTree(cateList.value)
      const draggedItem = flat.find((item: CategoryRow) => String(item.id) === draggedId)
      if (!draggedItem) return
      const parentId = draggedItem.parentId ?? null
      const idsAfterDrop = visibleRowIds()
      const candidateParent = findHoverMoveParent(draggedItem, lastMoveTargetParentId)
        || findBoundaryMoveParent(draggedItem, idsAfterDrop, originalEntries)
      lastMoveTargetParentId = null

      try {
        if (!candidateParent) {
          const siblingGroup = findSiblingGroup(cateList.value, parentId)
          const siblingIds = new Set(siblingGroup.map((item: CategoryRow) => String(item.id)))
          const orderedSiblingIds = idsAfterDrop.filter(id => siblingIds.has(id))
          const reorderItems = orderedSiblingIds.map((id, idx) => ({ id, sort: idx }))
          if (!reorderItems.length) {
            await fetchData()
            return
          }
          await productCategoryBatchSortAPI({ items: reorderItems })
          ElMessage.success('排序已更新')
          await fetchData()
          return
        }

        if (!candidateParent || String(candidateParent.id) === draggedId || collectDescendantIds(draggedItem).has(String(candidateParent.id))) {
          ElMessage.warning('不能移动到自身或自己的子分类下')
          await fetchData()
          return
        }

        await ElMessageBox.confirm(
          `是否将「${draggedItem.name}」作为「${candidateParent.name}」的子类？确认后分类级别会自动更新。`,
          '移动分类',
          { type: 'warning', confirmButtonText: '确认移动', cancelButtonText: '取消' },
        )
        await productCategoryMoveAPI(draggedId, candidateParent.id)
        ElMessage.success('分类层级已更新')
        await fetchData()
      } catch (error) {
        if (String((error as Error)?.message || error) !== 'cancel') {
          ElMessage.error('分类拖拽更新失败')
        }
        await fetchData()
      }
    },
  })
}

// ── 弹窗 ──
const dialogVisible = ref(false)
const dialogTitle = ref('')
const cateForm = ref<{
  id?: string; parentId: string | number | null; name: string;
  navStatus: number; showStatus: number; icon: string; keywords: string; description: string
}>({ id: undefined, parentId: 0, name: '', navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' })
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

function extractValidParentOptions(row?: any) {
  const blockedIds = new Set<string>()
  if (row?.id) {
    blockedIds.add(String(row.id))
    collectDescendantIds(row).forEach(id => blockedIds.add(id))
  }
  return extractParentOptions(cateList.value)
    .filter((option: any) => !blockedIds.has(String(option.value)))
    .filter((option: any) => (findCategory(option.value)?.level ?? 0) < 2)
}

function handleAdd(parentId = 0) {
  dialogTitle.value = '添加分类'
  parentOptions.value = [{ label: '无上级分类', value: 0 }, ...extractValidParentOptions()]
  cateForm.value = { id: undefined, parentId, name: '', navStatus: 1, showStatus: 1, icon: '', keywords: '', description: '' }
  dialogVisible.value = true
}

function handleEdit(row: any) {
  dialogTitle.value = '编辑分类'
  parentOptions.value = [{ label: '无上级分类', value: 0 }, ...extractValidParentOptions(row)]
  cateForm.value = { ...row, parentId: row.parentId ?? 0 }
  dialogVisible.value = true
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
    await productCategoryDeleteByIdAPI(row.id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (error) {
    const apiError = error as Error & { code?: string | number; status?: number }
    const message = String(apiError?.message || error)
    if (message === 'cancel') return
    if (apiError.code !== 'CATEGORY_DELETE_BLOCKED' && apiError.status !== 409 && !message.includes('无法删除分类')) {
      await fetchData()
      return
    }
    try {
      await ElMessageBox.confirm(
        `${message}\n\n强制删除会将该分类下商品变为未分类，并将子分类挂到上级分类。是否继续？`,
        '强制删除分类',
        { type: 'warning', confirmButtonText: '强制删除', cancelButtonText: '取消' },
      )
      await productCategoryDeleteByIdAPI(row.id, true)
      ElMessage.success('强制删除成功')
    } finally {
      await fetchData()
    }
  }
}

async function handleToggleNav(row: any, newVal: number) {
  try {
    await productCategoryUpdateNavStatusAPI(String(row.id), newVal)
    ElMessage.success('导航栏显示状态已更新')
    await fetchData()
  } catch {
    row.navStatus = newVal === 1 ? 0 : 1
  }
}

async function handleToggleShow(row: any, newVal: number) {
  try {
    await productCategoryUpdateShowStatusAPI(String(row.id), newVal)
    ElMessage.success('显示状态已更新')
    await fetchData()
  } catch {
    row.showStatus = newVal === 1 ? 0 : 1
  }
}

async function handleSaveCate() {
  if (!cateForm.value.name) return ElMessage.warning('请输入分类名称')
  try {
    if (cateForm.value.id) {
      await updateProductCategoryAPI(cateForm.value.id, cateForm.value as any)
      ElMessage.success('编辑成功')
    } else {
      await createProductCategoryAPI(cateForm.value as any)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch {
    await fetchData()
  }
}
</script>

<template>
  <div class="page-cate-list">
    <el-card class="toolbar-card" shadow="never">
      <el-button type="primary" :icon="Plus" @click="handleAdd(0)">添加分类</el-button>
      <span class="drag-tip">
        <el-icon><Rank /></el-icon>
        同级拖拽调整排序；跨级拖拽会询问是否移动为目标分类子类
      </span>
      <span class="sort-tip">排序值仅作用于同级分类，数值越小越靠前。</span>
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
        <el-table-column label="商品数" width="90" align="center">
          <template #default="{ row }">{{ row.productCount ?? 0 }}</template>
        </el-table-column>
        <el-table-column prop="sort" width="90" align="center">
          <template #header>
            <el-tooltip content="同级分类按排序值从小到大展示，拖拽会自动重写排序值。" placement="top">
              <span>排序</span>
            </el-tooltip>
          </template>
        </el-table-column>
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
    .sort-tip {
      color: #c0c4cc;
      font-size: 13px;
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
