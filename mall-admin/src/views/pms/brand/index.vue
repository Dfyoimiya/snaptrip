<script lang="ts" setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete, View } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索
const searchKeyword = ref('')
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(56)
const listLoading = ref(false)
const selectedRows = ref<any[]>([])

// 品牌数据
const brandList = ref([
  { id: 1, name: 'Apple', firstLetter: 'A', sort: 100, factoryStatus: 1, showStatus: 1, productCount: 86, productCommentCount: 2340, logo: 'https://picsum.photos/seed/applelogo/100/100', bigPic: '', brandStory: '苹果公司是全球知名的科技公司' },
  { id: 2, name: '华为', firstLetter: 'H', sort: 99, factoryStatus: 1, showStatus: 1, productCount: 128, productCommentCount: 5670, logo: 'https://picsum.photos/seed/huaweilogo/100/100', bigPic: '', brandStory: '华为技术有限公司是全球领先的信息与通信技术解决方案供应商' },
  { id: 3, name: '小米', firstLetter: 'X', sort: 98, factoryStatus: 1, showStatus: 1, productCount: 156, productCommentCount: 8900, logo: 'https://picsum.photos/seed/milogo/100/100', bigPic: '', brandStory: '小米是一家以手机、智能硬件和IoT平台为核心的互联网公司' },
  { id: 4, name: 'Nike', firstLetter: 'N', sort: 97, factoryStatus: 1, showStatus: 1, productCount: 68, productCommentCount: 1234, logo: 'https://picsum.photos/seed/nikelogo/100/100', bigPic: '', brandStory: 'Nike是全球著名的体育运动品牌' },
  { id: 5, name: 'Adidas', firstLetter: 'A', sort: 96, factoryStatus: 1, showStatus: 1, productCount: 54, productCommentCount: 987, logo: 'https://picsum.photos/seed/adidaslogo/100/100', bigPic: '', brandStory: '阿迪达斯是德国运动用品制造商' },
  { id: 6, name: '索尼', firstLetter: 'S', sort: 95, factoryStatus: 1, showStatus: 1, productCount: 42, productCommentCount: 1567, logo: 'https://picsum.photos/seed/sonylogo/100/100', bigPic: '', brandStory: '索尼是日本全球知名的大型综合性跨国企业集团' },
  { id: 7, name: '三星', firstLetter: 'S', sort: 94, factoryStatus: 0, showStatus: 1, productCount: 36, productCommentCount: 2100, logo: 'https://picsum.photos/seed/samsunglogo/100/100', bigPic: '', brandStory: '三星是韩国最大的跨国企业集团' },
  { id: 8, name: 'OPPO', firstLetter: 'O', sort: 93, factoryStatus: 1, showStatus: 0, productCount: 45, productCommentCount: 3456, logo: 'https://picsum.photos/seed/oppologo/100/100', bigPic: '', brandStory: 'OPPO是更多年轻人选择的拍照手机品牌' },
])

// 搜索
function handleSearch() {
  pageNum.value = 1
  ElMessage.success('搜索完成')
}
function handleReset() {
  searchKeyword.value = ''
  pageNum.value = 1
}

// 添加/编辑
function handleAdd() {
  brandDialogTitle.value = '添加品牌'
  brandForm.value = { id: undefined, name: '', firstLetter: '', sort: 0, factoryStatus: 1, showStatus: 1, logo: '', bigPic: '', brandStory: '' }
  brandDialogVisible.value = true
}
function handleEdit(row: any) {
  brandDialogTitle.value = '编辑品牌'
  brandForm.value = { ...row }
  brandDialogVisible.value = true
}
function handleDelete(row: any) {
  ElMessageBox.confirm(`确定删除品牌「${row.name}」吗？`, '提示', { type: 'warning' }).then(() => {
    brandList.value = brandList.value.filter(b => b.id !== row.id)
    ElMessage.success('删除成功')
  })
}

// 批量操作
function handleBatchDelete() {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个品牌？`, '提示', { type: 'warning' }).then(() => {
    const ids = selectedRows.value.map(r => r.id)
    brandList.value = brandList.value.filter(b => !ids.includes(b.id))
    ElMessage.success('批量删除成功')
  })
}
function handleBatchShow(status: number) {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  selectedRows.value.forEach(r => { const b = brandList.value.find(i => i.id === r.id); if (b) b.showStatus = status })
  ElMessage.success(status === 1 ? '批量显示成功' : '批量隐藏成功')
}
function handleBatchFactory(status: number) {
  if (selectedRows.value.length === 0) return ElMessage.warning('请至少选择一项')
  selectedRows.value.forEach(r => { const b = brandList.value.find(i => i.id === r.id); if (b) b.factoryStatus = status })
  ElMessage.success(status === 1 ? '批量设为制造商成功' : '批量取消制造商成功')
}

function handleSelectionChange(val: any[]) { selectedRows.value = val }

// 品牌表单弹窗
const brandDialogVisible = ref(false)
const brandDialogTitle = ref('')
const brandForm = ref({ id: undefined as number | undefined, name: '', firstLetter: '', sort: 0, factoryStatus: 1, showStatus: 1, logo: '', bigPic: '', brandStory: '' })

function handleSaveBrand() {
  if (!brandForm.value.name) return ElMessage.warning('请输入品牌名称')
  if (brandForm.value.id) {
    const idx = brandList.value.findIndex(b => b.id === brandForm.value.id)
    if (idx > -1) brandList.value[idx] = { ...brandForm.value, productCount: brandList.value[idx].productCount, productCommentCount: brandList.value[idx].productCommentCount }
    ElMessage.success('编辑成功')
  } else {
    brandList.value.unshift({ ...brandForm.value, id: Date.now(), productCount: 0, productCommentCount: 0 })
    ElMessage.success('添加成功')
  }
  brandDialogVisible.value = false
}
</script>

<template>
  <div class="page-brand-list">
    <!-- 搜索 -->
    <el-card class="search-card" shadow="never">
      <el-form inline>
        <el-form-item label="品牌名称">
          <el-input v-model="searchKeyword" placeholder="输入品牌名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <el-button type="primary" :icon="Plus" @click="handleAdd">添加品牌</el-button>
          <el-dropdown split-button type="danger" @click="handleBatchDelete">
            批量删除
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleBatchShow(1)">批量显示</el-dropdown-item>
                <el-dropdown-item @click="handleBatchShow(0)">批量隐藏</el-dropdown-item>
                <el-dropdown-item @click="handleBatchFactory(1)">批量设为制造商</el-dropdown-item>
                <el-dropdown-item @click="handleBatchFactory(0)">批量取消制造商</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>

      <el-table v-loading="listLoading" :data="brandList" style="width: 100%" @selection-change="handleSelectionChange" border>
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="60" align="center" />
        <el-table-column label="品牌Logo" width="90" align="center">
          <template #default="{ row }">
            <el-image v-if="row.logo" :src="row.logo" style="width: 50px; height: 50px; border-radius: 4px;" fit="cover" />
            <div v-else class="logo-placeholder">{{ row.name.charAt(0) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="品牌名称" prop="name" min-width="120" />
        <el-table-column label="首字母" prop="firstLetter" width="70" align="center" />
        <el-table-column label="排序" prop="sort" width="60" align="center" />
        <el-table-column label="制造商" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.factoryStatus" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="显示" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.showStatus" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="商品数量" prop="productCount" width="90" align="center" />
        <el-table-column label="评论数" prop="productCommentCount" width="80" align="center" />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pageNum" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" />
      </div>
    </el-card>

    <!-- 品牌弹窗 -->
    <el-dialog v-model="brandDialogVisible" :title="brandDialogTitle" width="600px" destroy-on-close>
      <el-form :model="brandForm" label-width="100px">
        <el-row :gutter="20">
          <el-col :xs="24" :lg="12">
            <el-form-item label="品牌名称" required>
              <el-input v-model="brandForm.name" placeholder="品牌名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="首字母">
              <el-input v-model="brandForm.firstLetter" placeholder="A-Z" maxlength="1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="排序">
              <el-input-number v-model="brandForm.sort" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="是否为制造商">
              <el-radio-group v-model="brandForm.factoryStatus">
                <el-radio :label="1">是</el-radio>
                <el-radio :label="0">否</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="是否显示">
              <el-radio-group v-model="brandForm.showStatus">
                <el-radio :label="1">是</el-radio>
                <el-radio :label="0">否</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="Logo链接">
              <el-input v-model="brandForm.logo" placeholder="Logo图片URL" />
            </el-form-item>
          </el-col>
          <el-col :xs="24">
            <el-form-item label="品牌故事">
              <el-input v-model="brandForm.brandStory" type="textarea" :rows="4" placeholder="品牌故事介绍" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="brandDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveBrand">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page-brand-list {
  .search-card { margin-bottom: 12px; border-radius: 8px; }
  .table-card { border-radius: 8px; }
  .table-header { display: flex; gap: 10px; }
  .pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
  .logo-placeholder {
    width: 50px; height: 50px; border-radius: 4px;
    background: linear-gradient(135deg, #165dff, #36cfc9);
    color: #fff; font-size: 20px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto;
  }
}
</style>
