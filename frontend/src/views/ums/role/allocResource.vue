<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchAllResourceList, getResourceCategoryListAllAPI } from '@/apis/resource'
import { getResourceByRoleIdAPI, roleAllocResourceAPI } from '@/apis/role'

const route = useRoute()
const router = useRouter()

const roleId = ref('')
const roleName = ref('')

interface ResourceItem {
  id: string
  categoryId?: string
  name?: string
  url?: string
  description?: string
  createTime?: string
}

interface CategoryItem {
  id: string
  name?: string
  sort?: number
}

const allResources = ref<ResourceItem[]>([])
const categoryList = ref<CategoryItem[]>([])
const categoryMap = ref<Record<string, string>>({})
const selectedIds = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref({ categoryId: undefined as string | undefined, keyword: '' })

const filteredList = computed(() => {
  let result = [...allResources.value]
  if (search.value.categoryId !== undefined && search.value.categoryId !== '') {
    result = result.filter(item => item.categoryId === search.value.categoryId)
  }
  if (search.value.keyword) {
    const kw = search.value.keyword
    result = result.filter(item =>
      (item.name && item.name.includes(kw)) ||
      (item.url && item.url.includes(kw))
    )
  }
  return result
})

async function loadData() {
  loading.value = true
  try {
    const [resourcesRes, categoriesRes, roleResourcesRes] = await Promise.all([
      fetchAllResourceList(),
      getResourceCategoryListAllAPI(),
      getResourceByRoleIdAPI(roleId.value),
    ])
    allResources.value = (resourcesRes.data as ResourceItem[]) || []
    const cats = (categoriesRes.data as CategoryItem[]) || []
    categoryList.value = cats
    categoryMap.value = {}
    cats.forEach(c => {
      if (c.id && c.name) categoryMap.value[c.id] = c.name
    })
    const roleData = (roleResourcesRes.data as ResourceItem[]) || []
    selectedIds.value = roleData.map(r => r.id).filter(Boolean)
  } catch {
    ElMessage.error('加载资源数据失败')
  } finally {
    loading.value = false
  }
}

function isRowSelected(row: ResourceItem) {
  return selectedIds.value.includes(row.id)
}

function handleSelectionChange(selection: ResourceItem[]) {
  const currentPageIds = filteredList.value.map(r => r.id)
  const otherIds = selectedIds.value.filter(id => !currentPageIds.includes(id))
  const newSelected = selection.map(s => s.id)
  selectedIds.value = [...otherIds, ...newSelected]
}

async function handleSave() {
  saving.value = true
  try {
    await roleAllocResourceAPI({ roleId: roleId.value, resourceIds: selectedIds.value.join(',') })
    ElMessage.success(`已为角色"${roleName.value || roleId.value}"分配 ${selectedIds.value.length} 个资源权限`)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function handleBack() {
  router.back()
}

function getCategoryName(categoryId: string) {
  return categoryMap.value[categoryId] || '-'
}

onMounted(() => {
  const id = route.query.roleId as string
  if (!id) {
    ElMessage.error('角色ID不能为空，请从角色列表进入')
    router.replace('/ums/role')
    return
  }
  roleId.value = id
  roleName.value = (route.query.roleName as string) || ''
  loadData()
})

watch(() => route.query.roleId, (newId) => {
  if (newId) {
    roleId.value = newId as string
    roleName.value = (route.query.roleName as string) || ''
    loadData()
  }
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <el-button link @click="handleBack">
              <el-icon><ArrowLeft /></el-icon>返回
            </el-button>
            <span style="margin-left: 12px; font-weight: 600">
              分配资源 — 角色：{{ roleName || roleId }}
            </span>
            <el-tag type="info" size="small" style="margin-left: 8px">roleId: {{ roleId }}</el-tag>
          </div>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>保存分配
          </el-button>
        </div>
      </template>

      <el-alert
        title="勾选该角色可以访问的资源，保存后生效"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />

      <!-- 筛选 -->
      <el-form inline style="margin-bottom: 16px">
        <el-form-item label="资源分类">
          <el-select v-model="search.categoryId" placeholder="全部分类" clearable style="width: 160px">
            <el-option
              v-for="cat in categoryList"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="资源名称/路径">
          <el-input v-model="search.keyword" placeholder="搜索" clearable style="width: 200px" />
        </el-form-item>
      </el-form>

      <!-- 资源表格 -->
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredList"
        border
        style="width: 100%"
        @selection-change="handleSelectionChange"
        :row-key="(row: ResourceItem) => row.id"
      >
        <el-table-column type="selection" width="55" align="center" reserve-selection />
        <el-table-column label="资源名称" prop="name" min-width="180" />
        <el-table-column label="资源路径" prop="url" min-width="200" />
        <el-table-column label="资源分类" width="140" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryName(row.categoryId || '') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="描述" prop="description" min-width="180" show-overflow-tooltip />
      </el-table>

      <!-- 统计 -->
      <div style="margin-top: 16px; color: #606266; font-size: 14px">
        已选择 <strong style="color: #409eff">{{ selectedIds.length }}</strong> 个资源
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.app-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
