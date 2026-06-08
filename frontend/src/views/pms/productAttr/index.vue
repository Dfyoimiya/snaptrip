<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, ArrowRight } from '@element-plus/icons-vue'
import {
  productAttributeCategoryListWithAttrAPI,
  productAttributeCategoryCreateAPI,
  productAttributeCategoryUpdateAPI,
  productAttributeCategoryDeleteById,
} from '@/apis/productAttrCate'
import {
  createProductAttributeAPI,
  updateProductAttributeAPI,
  deleteProductAttributeAPI,
} from '@/apis/productAttr'
import type { PmsProductAttributeCategoryExt, PmsProductAttribute } from '@/types/productAttr'

// ========== 属性分类 ==========
const attrCateList = ref<PmsProductAttributeCategoryExt[]>([])
const loading = ref(false)

const cateDialogVisible = ref(false)
const cateDialogTitle = ref('')
const cateForm = ref<{ id?: number; name: string }>({ id: undefined, name: '' })

async function fetchCateList() {
  loading.value = true
  try {
    const data = await productAttributeCategoryListWithAttrAPI()
    attrCateList.value = data || []
    if (attrCateList.value.length > 0 && !attrCateList.value.find(c => c.id === currentCateId.value)) {
      currentCateId.value = attrCateList.value[0].id!
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '获取分类列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchCateList()
})

function handleAddCate() {
  cateDialogTitle.value = '添加属性分类'
  cateForm.value = { id: undefined, name: '' }
  cateDialogVisible.value = true
}
function handleEditCate(row: any) {
  cateDialogTitle.value = '编辑属性分类'
  cateForm.value = { ...row }
  cateDialogVisible.value = true
}
async function handleDeleteCate(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
    await productAttributeCategoryDeleteById(row.id)
    ElMessage.success('删除成功')
    fetchCateList()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
  }
}
async function handleSaveCate() {
  if (!cateForm.value.name) return ElMessage.warning('请输入名称')
  try {
    if (cateForm.value.id) {
      await productAttributeCategoryUpdateAPI(cateForm.value.id, cateForm.value.name)
      ElMessage.success('编辑成功')
    } else {
      await productAttributeCategoryCreateAPI(cateForm.value.name)
      ElMessage.success('添加成功')
    }
    cateDialogVisible.value = false
    fetchCateList()
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
}

// ========== 属性列表 ==========
const currentCateId = ref(1)
const activeTab = ref('spec') // spec | param

const filteredAttrList = computed(() => {
  const cate = attrCateList.value.find(c => c.id === currentCateId.value)
  if (!cate || !cate.productAttributeList) return []
  return cate.productAttributeList.filter(a => a.type === (activeTab.value === 'spec' ? 0 : 1))
})

// 属性弹窗
const attrDialogVisible = ref(false)
const attrDialogTitle = ref('')
const attrForm = ref<PmsProductAttribute>({
  id: undefined,
  productAttributeCategoryId: 1,
  name: '',
  selectType: 1,
  inputType: 0,
  inputList: '',
  sort: 0,
  type: 0,
  handAddStatus: 0,
  searchType: 0,
  relatedStatus: 0,
})

function handleAddAttr() {
  attrDialogTitle.value = '添加' + (activeTab.value === 'spec' ? '规格' : '参数')
  attrForm.value = { id: undefined, productAttributeCategoryId: currentCateId.value, name: '', selectType: 1, inputType: 0, inputList: '', sort: 0, type: activeTab.value === 'spec' ? 0 : 1, handAddStatus: 0, searchType: 0, relatedStatus: 0 }
  attrDialogVisible.value = true
}
function handleEditAttr(row: any) {
  attrDialogTitle.value = '编辑' + (activeTab.value === 'spec' ? '规格' : '参数')
  attrForm.value = { ...row }
  attrDialogVisible.value = true
}
async function handleDeleteAttr(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
    await deleteProductAttributeAPI({ ids: String(row.id) })
    ElMessage.success('删除成功')
    fetchCateList()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
  }
}
async function handleSaveAttr() {
  if (!attrForm.value.name) return ElMessage.warning('请输入属性名称')
  try {
    if (attrForm.value.id) {
      await updateProductAttributeAPI(attrForm.value.id, attrForm.value)
      ElMessage.success('编辑成功')
    } else {
      await createProductAttributeAPI(attrForm.value)
      ElMessage.success('添加成功')
    }
    attrDialogVisible.value = false
    fetchCateList()
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
}

function selectCateType(cateId: number) {
  currentCateId.value = cateId
}
</script>

<template>
  <div class="page-attr-list">
    <el-row :gutter="12">
      <!-- 左侧属性分类 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="never" class="cate-card">
          <template #header>
            <div class="cate-header">
              <span>属性分类</span>
              <el-button link type="primary" :icon="Plus" @click="handleAddCate">添加</el-button>
            </div>
          </template>
          <div class="cate-list">
            <div
              v-for="cate in attrCateList"
              :key="cate.id"
              class="cate-item"
              :class="{ active: currentCateId === cate.id }"
              @click="selectCateType(cate.id)"
            >
              <div class="cate-name">{{ cate.name }}</div>
              <div class="cate-count">属性 {{ cate.attributeCount }} / 参数 {{ cate.paramCount }}</div>
              <div class="cate-actions">
                <el-button link type="primary" size="small" @click.stop="handleEditCate(cate)">编辑</el-button>
                <el-button link type="danger" size="small" @click.stop="handleDeleteCate(cate)">删除</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧属性列表 -->
      <el-col :xs="24" :lg="18">
        <el-card shadow="never" class="attr-card">
          <template #header>
            <div class="attr-header">
              <el-tabs v-model="activeTab" class="attr-tabs">
                <el-tab-pane label="规格列表" name="spec" />
                <el-tab-pane label="参数列表" name="param" />
              </el-tabs>
              <el-button type="primary" :icon="Plus" size="small" @click="handleAddAttr">
                添加{{ activeTab === 'spec' ? '规格' : '参数' }}
              </el-button>
            </div>
          </template>

          <el-table :data="filteredAttrList" border style="width: 100%">
            <el-table-column label="编号" prop="id" width="60" align="center" />
            <el-table-column label="属性名称" prop="name" min-width="140" />
            <el-table-column label="可选值列表" prop="inputList" min-width="200" show-overflow-tooltip />
            <el-table-column label="录入方式" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.inputType === 0" size="small" type="primary">手动录入</el-tag>
                <el-tag v-else size="small" type="success">从列表选</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="可选值类型" width="90" align="center">
              <template #default="{ row }">
                <span v-if="row.selectType === 0">单选</span>
                <span v-else-if="row.selectType === 1">多选</span>
                <span v-else>唯一</span>
              </template>
            </el-table-column>
            <el-table-column label="检索" width="70" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.searchType" :active-value="1" :inactive-value="0" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="排序" prop="sort" width="60" align="center" />
            <el-table-column label="操作" width="150" align="center" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :icon="Edit" size="small" @click="handleEditAttr(row)">编辑</el-button>
                <el-button link type="danger" :icon="Delete" size="small" @click="handleDeleteAttr(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="filteredAttrList.length === 0" class="empty-tip">
            暂无{{ activeTab === 'spec' ? '规格' : '参数' }}数据
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 属性分类弹窗 -->
    <el-dialog v-model="cateDialogVisible" :title="cateDialogTitle" width="400px" destroy-on-close>
      <el-form :model="cateForm" label-width="80px">
        <el-form-item label="分类名称" required>
          <el-input v-model="cateForm.name" placeholder="属性分类名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 属性弹窗 -->
    <el-dialog v-model="attrDialogVisible" :title="attrDialogTitle" width="600px" destroy-on-close>
      <el-form :model="attrForm" label-width="100px">
        <el-form-item label="属性名称" required>
          <el-input v-model="attrForm.name" placeholder="属性名称" />
        </el-form-item>
        <el-form-item label="可选值列表">
          <el-input v-model="attrForm.inputList" placeholder="用逗号分隔，如：黑色,白色,蓝色" />
        </el-form-item>
        <el-form-item label="录入方式">
          <el-radio-group v-model="attrForm.inputType">
            <el-radio :label="0">手动录入</el-radio>
            <el-radio :label="1">从可选值列表选择</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="可选值类型">
          <el-radio-group v-model="attrForm.selectType">
            <el-radio :label="0">单选</el-radio>
            <el-radio :label="1">多选</el-radio>
            <el-radio :label="2">唯一</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="能否检索">
          <el-radio-group v-model="attrForm.searchType">
            <el-radio :label="1">是</el-radio>
            <el-radio :label="0">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="支持手动新增">
          <el-radio-group v-model="attrForm.handAddStatus">
            <el-radio :label="1">是</el-radio>
            <el-radio :label="0">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="attrForm.sort" :min="0" style="width: 200px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="attrDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveAttr">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page-attr-list {
  .cate-card { border-radius: 8px; }
  .cate-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
  .cate-list { display: flex; flex-direction: column; gap: 4px; }
  .cate-item {
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;
    .cate-name { font-size: 14px; font-weight: 500; color: #1f2229; margin-bottom: 4px; }
    .cate-count { font-size: 12px; color: #86909c; }
    .cate-actions { margin-top: 8px; opacity: 0; transition: opacity 0.2s; }
    &:hover {
      background: #f7f8fa;
      border-color: #e5e6eb;
      .cate-actions { opacity: 1; }
    }
    &.active {
      background: #e8f4ff;
      border-color: #165dff;
      .cate-name { color: #165dff; }
    }
  }
  .attr-card { border-radius: 8px; }
  .attr-header { display: flex; justify-content: space-between; align-items: center; }
  .attr-tabs { margin-bottom: -18px; }
  .empty-tip { text-align: center; padding: 40px; color: #86909c; font-size: 14px; }
}
</style>
