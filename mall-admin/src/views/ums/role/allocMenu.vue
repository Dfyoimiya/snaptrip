<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const roleId = ref<number>(Number(route.query.roleId) || 0)

// 角色列表（用于显示角色名称）
const roleMap: Record<number, string> = {
  1: '超级管理员',
  2: '商品管理员',
  3: '订单管理员',
  4: '会员管理员',
  5: '运营人员',
  6: '客服人员',
  7: '财务人员',
}

// 所有菜单树
const menuTree = ref([
  {
    id: 1,
    title: '商品管理',
    children: [
      { id: 2, title: '商品列表' },
      { id: 3, title: '添加商品' },
      { id: 4, title: '商品分类' },
      { id: 5, title: '商品类型' },
      { id: 13, title: '品牌管理' },
    ],
  },
  {
    id: 6,
    title: '订单管理',
    children: [
      { id: 7, title: '订单列表' },
      { id: 8, title: '订单设置' },
      { id: 9, title: '退货申请' },
      { id: 14, title: '退货原因' },
    ],
  },
  {
    id: 10,
    title: '会员管理',
    children: [
      { id: 11, title: '用户管理' },
      { id: 12, title: '角色管理' },
      { id: 15, title: '菜单管理' },
      { id: 16, title: '资源管理' },
    ],
  },
  {
    id: 18,
    title: '营销管理',
    children: [
      { id: 19, title: '优惠券' },
      { id: 20, title: '秒杀活动' },
      { id: 21, title: '品牌推荐' },
    ],
  },
  {
    id: 22,
    title: '内容管理',
    children: [
      { id: 23, title: '轮播广告' },
      { id: 24, title: '专题管理' },
    ],
  },
  {
    id: 25,
    title: '系统设置',
    children: [
      { id: 26, title: '文件存储' },
    ],
  },
])

// 每个角色已分配的菜单ID（模拟角色-菜单关联数据）
const roleMenuMap: Record<number, number[]> = {
  1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26], // 超级管理员：全部
  2: [1, 2, 3, 4, 5, 13], // 商品管理员
  3: [6, 7, 8, 9, 14], // 订单管理员
  4: [10, 11, 12, 15, 16], // 会员管理员
  5: [1, 2, 4, 6, 7, 18, 19, 20, 21, 22, 23, 24, 25, 26], // 运营人员
  6: [6, 7, 9, 10, 11], // 客服人员
  7: [6, 7, 8], // 财务人员
}

const checkedKeys = ref<number[]>([])
const treeRef = ref()
const loading = ref(false)
const saving = ref(false)

function loadRoleMenus() {
  loading.value = true
  setTimeout(() => {
    checkedKeys.value = roleMenuMap[roleId.value] || []
    loading.value = false
  }, 200)
}

async function handleSave() {
  saving.value = true
  const checked = treeRef.value?.getCheckedKeys() || []
  const halfChecked = treeRef.value?.getHalfCheckedKeys() || []
  const allChecked = [...checked, ...halfChecked]

  // 模拟保存
  setTimeout(() => {
    roleMenuMap[roleId.value] = allChecked
    ElMessage.success(`已为角色"${roleMap[roleId.value] || '未知'}"分配 ${allChecked.length} 个菜单权限`)
    saving.value = false
  }, 300)
}

function handleBack() {
  router.back()
}

onMounted(() => {
  if (!roleId.value) {
    ElMessage.error('角色ID不能为空')
    router.back()
    return
  }
  loadRoleMenus()
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
              分配菜单 — 角色：{{ roleMap[roleId] || '未知' }}
            </span>
            <el-tag type="info" size="small" style="margin-left: 8px">roleId: {{ roleId }}</el-tag>
          </div>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>保存分配
          </el-button>
        </div>
      </template>

      <el-alert
        title="勾选该角色可以访问的菜单，保存后生效"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />

      <el-tree
        ref="treeRef"
        v-loading="loading"
        :data="menuTree"
        show-checkbox
        node-key="id"
        :default-checked-keys="checkedKeys"
        :props="{ label: 'title', children: 'children' }"
        default-expand-all
        style="max-width: 500px"
      />
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
