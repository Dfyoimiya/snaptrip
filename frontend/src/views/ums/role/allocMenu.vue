<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMenuTreeListAPI } from '@/apis/menu'
import { getMenuByRoleIdAPI, roleAllocMenuAPI } from '@/apis/role'

const route = useRoute()
const router = useRouter()

const roleId = ref('')
const roleName = ref('')

const menuTree = ref<any[]>([])
const checkedKeys = ref<string[]>([])
const treeRef = ref()
const loading = ref(false)
const saving = ref(false)

async function loadMenuData() {
  loading.value = true
  try {
    const [tree, roleMenus] = await Promise.all([
      getMenuTreeListAPI(),
      getMenuByRoleIdAPI(roleId.value),
    ])
    menuTree.value = (tree.data as any) || []
    const roleMenuData = roleMenus.data || []
    checkedKeys.value = roleMenuData.map((m: any) => m.id).filter(Boolean)
  } catch {
    ElMessage.error('加载菜单数据失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const checked = treeRef.value?.getCheckedKeys() || []
    const halfChecked = treeRef.value?.getHalfCheckedKeys() || []
    const allChecked = [...checked, ...halfChecked]
    await roleAllocMenuAPI({ roleId: roleId.value, menuIds: allChecked.join(',') })
    ElMessage.success(`已为角色"${roleName.value || roleId.value}"分配 ${allChecked.length} 个菜单权限`)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function handleBack() {
  router.back()
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
  loadMenuData()
})

watch(() => route.query.roleId, (newId) => {
  if (newId) {
    roleId.value = newId as string
    roleName.value = (route.query.roleName as string) || ''
    loadMenuData()
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
              分配菜单 — 角色：{{ roleName || roleId }}
            </span>
            <el-tag type="info" size="small" style="margin-left: 8px">角色编号：{{ roleId }}</el-tag>
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
