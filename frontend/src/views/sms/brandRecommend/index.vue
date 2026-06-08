<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchHomeBrandList,
  addHomeBrand,
  updateHomeBrandSort,
  updateHomeBrandStatus,
  deleteHomeBrand,
  batchDeleteHomeBrand,
} from '@/apis/homeBrand'
import type { SmsHomeBrand } from '@/types/homeBrand'

const loading = ref(false)
const list = ref<SmsHomeBrand[]>([])
const search = reactive({
  brandName: '',
  recommendStatus: '' as number | '',
})
const selectedIds = ref<number[]>([])

// 可选择的品牌列表（用于"选择品牌"弹窗）
const allBrands = [
  { id: 5, name: '三星' },
  { id: 8, name: '阿迪达斯' },
  { id: 9, name: '兰蔻' },
  { id: 10, name: '雅诗兰黛' },
  { id: 11, name: '乐高' },
  { id: 12, name: 'Nintendo' },
  { id: 13, name: '宜家' },
  { id: 14, name: '无印良品' },
]

const brandDialogVisible = ref(false)
const selectedBrandIds = ref<number[]>([])

const filteredList = computed(() => {
  let result = list.value
  if (search.brandName) {
    result = result.filter(item => item.brandName?.includes(search.brandName))
  }
  if (search.recommendStatus !== '') {
    result = result.filter(item => item.recommendStatus === search.recommendStatus)
  }
  return result
})

async function loadList() {
  loading.value = true
  try {
    const res = await fetchHomeBrandList({})
    list.value = res.data.list
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  // 本地筛选，computed 已实现
}

function handleReset() {
  search.brandName = ''
  search.recommendStatus = ''
}

function handleSelectionChange(selection: SmsHomeBrand[]) {
  selectedIds.value = selection.map(item => item.id!).filter(Boolean)
}

// 推荐状态
async function handleToggleStatus(row: SmsHomeBrand) {
  const newStatus = row.recommendStatus === 1 ? 0 : 1
  await updateHomeBrandStatus(row.id!, newStatus)
  row.recommendStatus = newStatus
  ElMessage.success('状态更新成功')
}

// 排序
function handleSortChange(row: SmsHomeBrand) {
  updateHomeBrandSort(row.id!, row.sort || 0)
}

// 删除
async function handleDelete(row: SmsHomeBrand) {
  try {
    await ElMessageBox.confirm(`确定取消品牌"${row.brandName}"的推荐吗？`, '提示', { type: 'warning' })
    await deleteHomeBrand(row.id!)
    ElMessage.success('删除成功')
    loadList()
  } catch {
    // cancel
  }
}

// 批量删除
async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请至少选择一项')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 项吗？`, '提示', { type: 'warning' })
    await batchDeleteHomeBrand(selectedIds.value)
    ElMessage.success('批量删除成功')
    loadList()
  } catch {
    // cancel
  }
}

// 选择品牌
function handleSelectBrand() {
  selectedBrandIds.value = []
  brandDialogVisible.value = true
}

async function handleConfirmSelectBrand() {
  if (selectedBrandIds.value.length === 0) {
    ElMessage.warning('请至少选择一个品牌')
    return
  }
  for (const brandId of selectedBrandIds.value) {
    const brand = allBrands.find(b => b.id === brandId)
    if (brand) {
      await addHomeBrand({
        brandId: brand.id,
        brandName: brand.name,
        recommendStatus: 1,
        sort: 100,
      })
    }
  }
  ElMessage.success('添加成功')
  brandDialogVisible.value = false
  loadList()
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="search" inline>
        <el-form-item label="品牌名称">
          <el-input v-model="search.brandName" placeholder="品牌名称" clearable />
        </el-form-item>
        <el-form-item label="推荐状态">
          <el-select v-model="search.recommendStatus" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="推荐中" :value="1" />
            <el-option label="未推荐" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>品牌推荐列表</span>
          <div>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>批量删除
            </el-button>
            <el-button type="primary" size="small" @click="handleSelectBrand" style="margin-left: 8px">
              <el-icon><Plus /></el-icon>选择品牌
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="filteredList"
        border
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="编号" prop="id" width="80" align="center" />
        <el-table-column label="品牌名称" prop="brandName" min-width="150" />
        <el-table-column label="是否推荐" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.recommendStatus"
              :active-value="1"
              :inactive-value="0"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="排序" prop="sort" width="120" align="center">
          <template #default="{ row }">
            <el-input-number v-model="row.sort" :min="0" size="small" style="width: 90px" @change="handleSortChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="createTime" width="160" align="center" />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 选择品牌弹窗 -->
    <el-dialog v-model="brandDialogVisible" title="选择推荐品牌" width="480px" destroy-on-close>
      <el-checkbox-group v-model="selectedBrandIds">
        <el-space wrap>
          <el-checkbox-button
            v-for="brand in allBrands"
            :key="brand.id"
            :label="brand.id"
            :value="brand.id"
          >
            {{ brand.name }}
          </el-checkbox-button>
        </el-space>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="brandDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmSelectBrand">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.app-container {
  padding: 20px;
}
.search-card {
  :deep(.el-card__body) {
    padding-bottom: 0;
  }
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
