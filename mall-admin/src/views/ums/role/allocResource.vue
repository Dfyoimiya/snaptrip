<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const roleId = ref<number>(Number(route.query.roleId) || 0)

// 角色列表
const roleMap: Record<number, string> = {
  1: '超级管理员',
  2: '商品管理员',
  3: '订单管理员',
  4: '会员管理员',
  5: '运营人员',
  6: '客服人员',
  7: '财务人员',
}

// 资源分类
const categoryMap: Record<number, string> = {
  1: '商品模块',
  2: '订单模块',
  3: '会员模块',
  4: '营销模块',
  5: '权限模块',
}

// 所有资源列表
const allResources = ref([
  { id: 1, categoryId: 1, name: '商品列表查询', url: '/product/list', description: '查询商品列表' },
  { id: 2, categoryId: 1, name: '商品添加', url: '/product/create', description: '添加商品' },
  { id: 3, categoryId: 1, name: '商品修改', url: '/product/update', description: '修改商品' },
  { id: 4, categoryId: 1, name: '商品删除', url: '/product/delete', description: '删除商品' },
  { id: 5, categoryId: 1, name: '商品分类查询', url: '/productCategory/list', description: '查询商品分类' },
  { id: 6, categoryId: 1, name: '商品分类修改', url: '/productCategory/update', description: '修改商品分类' },
  { id: 7, categoryId: 1, name: '商品类型查询', url: '/productAttribute/list', description: '查询商品类型' },
  { id: 8, categoryId: 1, name: '品牌查询', url: '/brand/list', description: '查询品牌列表' },
  { id: 9, categoryId: 1, name: '品牌修改', url: '/brand/update', description: '修改品牌信息' },
  { id: 10, categoryId: 2, name: '订单列表查询', url: '/order/list', description: '查询订单列表' },
  { id: 11, categoryId: 2, name: '订单详情查看', url: '/order/detail', description: '查看订单详情' },
  { id: 12, categoryId: 2, name: '订单关闭', url: '/order/close', description: '关闭订单' },
  { id: 13, categoryId: 2, name: '订单删除', url: '/order/delete', description: '删除订单' },
  { id: 14, categoryId: 2, name: '订单设置修改', url: '/orderSetting/update', description: '修改订单设置' },
  { id: 15, categoryId: 2, name: '退货申请处理', url: '/returnApply/update', description: '处理退货申请' },
  { id: 16, categoryId: 2, name: '退货原因管理', url: '/returnReason/list', description: '查询退货原因' },
  { id: 17, categoryId: 3, name: '用户列表查询', url: '/admin/list', description: '查询用户列表' },
  { id: 18, categoryId: 3, name: '用户添加', url: '/admin/create', description: '添加用户' },
  { id: 19, categoryId: 3, name: '用户修改', url: '/admin/update', description: '修改用户信息' },
  { id: 20, categoryId: 3, name: '用户删除', url: '/admin/delete', description: '删除用户' },
  { id: 21, categoryId: 3, name: '角色列表查询', url: '/role/list', description: '查询角色列表' },
  { id: 22, categoryId: 3, name: '角色修改', url: '/role/update', description: '修改角色信息' },
  { id: 23, categoryId: 3, name: '菜单列表查询', url: '/menu/list', description: '查询菜单列表' },
  { id: 24, categoryId: 3, name: '资源列表查询', url: '/resource/list', description: '查询资源列表' },
  { id: 25, categoryId: 4, name: '优惠券查询', url: '/coupon/list', description: '查询优惠券' },
  { id: 26, categoryId: 4, name: '优惠券添加', url: '/coupon/create', description: '添加优惠券' },
  { id: 27, categoryId: 4, name: '优惠券修改', url: '/coupon/update', description: '修改优惠券' },
  { id: 28, categoryId: 4, name: '秒杀活动查询', url: '/flash/list', description: '查询秒杀活动' },
  { id: 29, categoryId: 4, name: '秒杀活动修改', url: '/flash/update', description: '修改秒杀活动' },
  { id: 30, categoryId: 4, name: '品牌推荐查询', url: '/homeBrand/list', description: '查询品牌推荐' },
  { id: 31, categoryId: 5, name: '角色分配菜单', url: '/role/allocMenu', description: '为角色分配菜单' },
  { id: 32, categoryId: 5, name: '角色分配资源', url: '/role/allocResource', description: '为角色分配资源' },
])

// 每个角色已分配的资源ID（模拟角色-资源关联数据）
const roleResourceMap: Record<number, number[]> = {
  1: allResources.value.map(r => r.id), // 超级管理员：全部
  2: [1, 2, 3, 4, 5, 6, 7, 8, 9], // 商品管理员
  3: [10, 11, 12, 13, 14, 15, 16], // 订单管理员
  4: [17, 18, 19, 20, 21, 22, 23, 24, 31, 32], // 会员管理员
  5: [1, 2, 4, 5, 10, 11, 25, 26, 27, 28, 29, 30], // 运营人员
  6: [10, 11, 12, 15, 17], // 客服人员
  7: [10, 11, 14], // 财务人员
}

const selectedIds = ref<number[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref({ categoryId: undefined as number | undefined, keyword: '' })

const filteredList = computed(() => {
  let result = [...allResources.value]
  if (search.value.categoryId !== undefined) {
    result = result.filter(item => item.categoryId === search.value.categoryId)
  }
  if (search.value.keyword) {
    result = result.filter(item => item.name.includes(search.value.keyword) || item.url.includes(search.value.keyword))
  }
  return result
})

function loadRoleResources() {
  loading.value = true
  setTimeout(() => {
    selectedIds.value = roleResourceMap[roleId.value] || []
    loading.value = false
  }, 200)
}

function handleSelectionChange(selection: any[]) {
  // 只处理当前页选中项，累加到全局
  const currentPageIds = filteredList.value.map(r => r.id)
  const otherIds = selectedIds.value.filter(id => !currentPageIds.includes(id))
  const newSelected = selection.map(s => s.id)
  selectedIds.value = [...otherIds, ...newSelected]
}

// 表格行是否选中
function isRowSelected(row: any) {
  return selectedIds.value.includes(row.id)
}

async function handleSave() {
  saving.value = true
  setTimeout(() => {
    roleResourceMap[roleId.value] = [...selectedIds.value]
    ElMessage.success(`已为角色"${roleMap[roleId.value] || '未知'}"分配 ${selectedIds.value.length} 个资源权限`)
    saving.value = false
  }, 300)
}

function handleBack() {
  router.back()
}

function getCategoryName(categoryId: number) {
  return categoryMap[categoryId] || '-'
}

onMounted(() => {
  if (!roleId.value) {
    ElMessage.error('角色ID不能为空')
    router.back()
    return
  }
  loadRoleResources()
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
              分配资源 — 角色：{{ roleMap[roleId] || '未知' }}
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
          <el-select v-model="search.categoryId" placeholder="全部分类" clearable style="width: 140px">
            <el-option v-for="(label, id) in categoryMap" :key="id" :label="label" :value="Number(id)" />
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
        :row-key="(row: any) => row.id"
      >
        <el-table-column type="selection" width="55" align="center" reserve-selection />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="资源名称" prop="name" min-width="150" />
        <el-table-column label="资源路径" prop="url" min-width="180" />
        <el-table-column label="资源分类" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryName(row.categoryId) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="描述" prop="description" min-width="150" show-overflow-tooltip />
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
