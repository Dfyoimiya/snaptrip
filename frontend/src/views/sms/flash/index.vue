<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchFlashPromotionList,
  saveFlashPromotion,
  deleteFlashPromotion,
  updateFlashPromotionStatus,
  fetchSessionList,
  saveSession,
  deleteSession,
  updateSessionStatus,
  fetchFlashProductList,
  saveFlashProduct,
  deleteFlashProduct,
} from '@/apis/flash'
import type { SmsFlashPromotion, SmsFlashPromotionSession, SmsFlashPromotionProduct } from '@/types/flash'

// ========== Tab 状态 ==========
const activeTab = ref('activity')

// ========== 秒杀活动 ==========
const activityLoading = ref(false)
const activityList = ref<SmsFlashPromotion[]>([])
const activitySearch = reactive({ keyword: '', status: '' as number | '' })
const activityDialogVisible = ref(false)
const activityDialogTitle = ref('添加活动')
const activityForm = reactive<SmsFlashPromotion>({
  id: undefined,
  title: '',
  startDate: '',
  endDate: '',
  status: 1,
})
const activityFormRef = ref()
const activityRules = {
  title: [{ required: true, message: '请输入活动名称', trigger: 'blur' }],
  startDate: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  endDate: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
}

const filteredActivityList = computed(() => {
  let list = activityList.value
  if (activitySearch.keyword) {
    list = list.filter(item => item.title?.includes(activitySearch.keyword))
  }
  if (activitySearch.status !== '') {
    list = list.filter(item => item.status === activitySearch.status)
  }
  return list
})

async function loadActivityList() {
  activityLoading.value = true
  try {
    const res = await fetchFlashPromotionList({})
    activityList.value = res.data.list
  } catch {
    ElMessage.error('加载失败')
  } finally {
    activityLoading.value = false
  }
}

function handleSearchActivity() {
  // 本地搜索，已用 computed 实现
}

function handleResetActivity() {
  activitySearch.keyword = ''
  activitySearch.status = ''
}

function handleAddActivity() {
  activityDialogTitle.value = '添加活动'
  Object.assign(activityForm, {
    id: undefined,
    title: '',
    startDate: '',
    endDate: '',
    status: 1,
  })
  activityDialogVisible.value = true
}

function handleEditActivity(row: SmsFlashPromotion) {
  activityDialogTitle.value = '编辑活动'
  Object.assign(activityForm, { ...row })
  activityDialogVisible.value = true
}

async function handleSaveActivity() {
  const valid = await activityFormRef.value?.validate().catch(() => false)
  if (!valid) return
  await saveFlashPromotion({ ...activityForm })
  ElMessage.success('保存成功')
  activityDialogVisible.value = false
  loadActivityList()
}

async function handleDeleteActivity(row: SmsFlashPromotion) {
  try {
    await ElMessageBox.confirm(`确定删除活动"${row.title}"吗？`, '提示', { type: 'warning' })
    await deleteFlashPromotion(row.id!)
    ElMessage.success('删除成功')
    loadActivityList()
  } catch {
    // cancel
  }
}

async function handleToggleActivityStatus(row: SmsFlashPromotion) {
  const newStatus = row.status === 1 ? 0 : 1
  await updateFlashPromotionStatus(row.id!, newStatus)
  row.status = newStatus
  ElMessage.success('状态更新成功')
}

// ========== 秒杀时段 ==========
const sessionLoading = ref(false)
const sessionList = ref<SmsFlashPromotionSession[]>([])
const sessionDialogVisible = ref(false)
const sessionDialogTitle = ref('添加时段')
const sessionForm = reactive<SmsFlashPromotionSession>({
  id: undefined,
  name: '',
  startTime: '',
  endTime: '',
  status: 1,
})
const sessionFormRef = ref()
const sessionRules = {
  name: [{ required: true, message: '请输入时段名称', trigger: 'blur' }],
  startTime: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  endTime: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

async function loadSessionList() {
  sessionLoading.value = true
  try {
    const res = await fetchSessionList()
    sessionList.value = res.data
  } catch {
    ElMessage.error('加载失败')
  } finally {
    sessionLoading.value = false
  }
}

function handleAddSession() {
  sessionDialogTitle.value = '添加时段'
  Object.assign(sessionForm, {
    id: undefined,
    name: '',
    startTime: '',
    endTime: '',
    status: 1,
  })
  sessionDialogVisible.value = true
}

function handleEditSession(row: SmsFlashPromotionSession) {
  sessionDialogTitle.value = '编辑时段'
  Object.assign(sessionForm, { ...row })
  sessionDialogVisible.value = true
}

async function handleSaveSession() {
  const valid = await sessionFormRef.value?.validate().catch(() => false)
  if (!valid) return
  await saveSession({ ...sessionForm })
  ElMessage.success('保存成功')
  sessionDialogVisible.value = false
  loadSessionList()
}

async function handleDeleteSession(row: SmsFlashPromotionSession) {
  try {
    await ElMessageBox.confirm(`确定删除时段"${row.name}"吗？`, '提示', { type: 'warning' })
    await deleteSession(row.id!)
    ElMessage.success('删除成功')
    loadSessionList()
  } catch {
    // cancel
  }
}

async function handleToggleSessionStatus(row: SmsFlashPromotionSession) {
  const newStatus = row.status === 1 ? 0 : 1
  await updateSessionStatus(row.id!, newStatus)
  row.status = newStatus
  ElMessage.success('状态更新成功')
}

// ========== 秒杀商品 ==========
const productLoading = ref(false)
const productList = ref<SmsFlashPromotionProduct[]>([])
const productSearch = reactive({
  flashPromotionId: undefined as number | undefined,
  flashPromotionSessionId: undefined as number | undefined,
})
const productDialogVisible = ref(false)
const productDialogTitle = ref('添加秒杀商品')
const productForm = reactive<SmsFlashPromotionProduct>({
  id: undefined,
  flashPromotionId: undefined,
  flashPromotionSessionId: undefined,
  productId: undefined,
  productName: '',
  productPrice: 0,
  flashPromotionPrice: 0,
  flashPromotionCount: 100,
  flashPromotionLimit: 1,
  sort: 0,
})
const productFormRef = ref()
const productRules = {
  flashPromotionId: [{ required: true, message: '请选择活动', trigger: 'change' }],
  flashPromotionSessionId: [{ required: true, message: '请选择时段', trigger: 'change' }],
  productName: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  flashPromotionPrice: [{ required: true, message: '请输入秒杀价格', trigger: 'blur' }],
  flashPromotionCount: [{ required: true, message: '请输入秒杀数量', trigger: 'blur' }],
}

async function loadProductList() {
  productLoading.value = true
  try {
    const res = await fetchFlashProductList({ ...productSearch })
    productList.value = res.data.list
  } catch {
    ElMessage.error('加载失败')
  } finally {
    productLoading.value = false
  }
}

function handleSearchProduct() {
  loadProductList()
}

function handleAddProduct() {
  productDialogTitle.value = '添加秒杀商品'
  Object.assign(productForm, {
    id: undefined,
    flashPromotionId: productSearch.flashPromotionId,
    flashPromotionSessionId: productSearch.flashPromotionSessionId,
    productId: undefined,
    productName: '',
    productPrice: 0,
    flashPromotionPrice: 0,
    flashPromotionCount: 100,
    flashPromotionLimit: 1,
    sort: 0,
  })
  productDialogVisible.value = true
}

function handleEditProduct(row: SmsFlashPromotionProduct) {
  productDialogTitle.value = '编辑秒杀商品'
  Object.assign(productForm, { ...row })
  productDialogVisible.value = true
}

async function handleSaveProduct() {
  const valid = await productFormRef.value?.validate().catch(() => false)
  if (!valid) return
  await saveFlashProduct({ ...productForm })
  ElMessage.success('保存成功')
  productDialogVisible.value = false
  loadProductList()
}

async function handleDeleteProduct(row: SmsFlashPromotionProduct) {
  try {
    await ElMessageBox.confirm(`确定删除商品"${row.productName}"吗？`, '提示', { type: 'warning' })
    await deleteFlashProduct(row.id!)
    ElMessage.success('删除成功')
    loadProductList()
  } catch {
    // cancel
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  loadActivityList()
  loadSessionList()
  loadProductList()
})
</script>

<template>
  <div class="app-container">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- ========== 秒杀活动列表 ========== -->
      <el-tab-pane label="秒杀活动列表" name="activity">
        <el-card shadow="never" class="search-card">
          <el-form :model="activitySearch" inline>
            <el-form-item label="活动名称">
              <el-input v-model="activitySearch.keyword" placeholder="活动名称" clearable />
            </el-form-item>
            <el-form-item label="活动状态">
              <el-select v-model="activitySearch.status" placeholder="全部状态" clearable style="width: 120px">
                <el-option label="上线" :value="1" />
                <el-option label="下线" :value="0" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchActivity">
                <el-icon><Search /></el-icon>查询
              </el-button>
              <el-button @click="handleResetActivity">
                <el-icon><Refresh /></el-icon>重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>秒杀活动列表</span>
              <el-button type="primary" size="small" @click="handleAddActivity">
                <el-icon><Plus /></el-icon>添加活动
              </el-button>
            </div>
          </template>

          <el-table v-loading="activityLoading" :data="filteredActivityList" border style="width: 100%">
            <el-table-column type="selection" width="55" align="center" />
            <el-table-column label="编号" prop="id" width="80" align="center" />
            <el-table-column label="活动名称" prop="title" min-width="200" show-overflow-tooltip />
            <el-table-column label="开始日期" prop="startDate" width="120" align="center" />
            <el-table-column label="结束日期" prop="endDate" width="120" align="center" />
            <el-table-column label="上下线状态" width="100" align="center">
              <template #default="{ row }">
                <el-switch
                  v-model="row.status"
                  :active-value="1"
                  :inactive-value="0"
                  @change="handleToggleActivityStatus(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" prop="createTime" width="160" align="center" />
            <el-table-column label="操作" width="200" fixed="right" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="handleEditActivity(row)">
                  <el-icon><Edit /></el-icon>编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDeleteActivity(row)">
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ========== 秒杀时间段 ========== -->
      <el-tab-pane label="秒杀时间段" name="session">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>秒杀时间段列表</span>
              <el-button type="primary" size="small" @click="handleAddSession">
                <el-icon><Plus /></el-icon>添加时段
              </el-button>
            </div>
          </template>

          <el-table v-loading="sessionLoading" :data="sessionList" border style="width: 100%">
            <el-table-column label="编号" prop="id" width="80" align="center" />
            <el-table-column label="时段名称" prop="name" min-width="120" />
            <el-table-column label="每日开始时间" prop="startTime" width="140" align="center" />
            <el-table-column label="每日结束时间" prop="endTime" width="140" align="center" />
            <el-table-column label="启用状态" width="100" align="center">
              <template #default="{ row }">
                <el-switch
                  v-model="row.status"
                  :active-value="1"
                  :inactive-value="0"
                  @change="handleToggleSessionStatus(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" prop="createTime" width="160" align="center" />
            <el-table-column label="操作" width="200" fixed="right" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="handleEditSession(row)">
                  <el-icon><Edit /></el-icon>编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDeleteSession(row)">
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ========== 秒杀商品 ========== -->
      <el-tab-pane label="秒杀商品列表" name="product">
        <el-card shadow="never" class="search-card">
          <el-form inline>
            <el-form-item label="活动">
              <el-select v-model="productSearch.flashPromotionId" placeholder="选择活动" clearable style="width: 200px">
                <el-option
                  v-for="item in activityList"
                  :key="item.id"
                  :label="item.title"
                  :value="item.id!"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="时段">
              <el-select v-model="productSearch.flashPromotionSessionId" placeholder="选择时段" clearable style="width: 150px">
                <el-option
                  v-for="item in sessionList"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id!"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchProduct">
                <el-icon><Search /></el-icon>查询
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>秒杀商品列表</span>
              <el-button type="primary" size="small" @click="handleAddProduct">
                <el-icon><Plus /></el-icon>添加商品
              </el-button>
            </div>
          </template>

          <el-table v-loading="productLoading" :data="productList" border style="width: 100%">
            <el-table-column type="selection" width="55" align="center" />
            <el-table-column label="编号" prop="id" width="80" align="center" />
            <el-table-column label="商品名称" prop="productName" min-width="180" show-overflow-tooltip />
            <el-table-column label="商品属性" prop="productAttr" width="150" show-overflow-tooltip />
            <el-table-column label="商品原价" prop="productPrice" width="100" align="center">
              <template #default="{ row }">
                <span>￥{{ row.productPrice }}</span>
              </template>
            </el-table-column>
            <el-table-column label="秒杀价" prop="flashPromotionPrice" width="100" align="center">
              <template #default="{ row }">
                <span style="color: #f56c6c; font-weight: bold">￥{{ row.flashPromotionPrice }}</span>
              </template>
            </el-table-column>
            <el-table-column label="秒杀数量" prop="flashPromotionCount" width="90" align="center" />
            <el-table-column label="每人限购" prop="flashPromotionLimit" width="90" align="center" />
            <el-table-column label="排序" prop="sort" width="70" align="center" />
            <el-table-column label="操作" width="180" fixed="right" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="handleEditProduct(row)">
                  <el-icon><Edit /></el-icon>编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDeleteProduct(row)">
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ========== 活动弹窗 ========== -->
    <el-dialog v-model="activityDialogVisible" :title="activityDialogTitle" width="560px" destroy-on-close>
      <el-form ref="activityFormRef" :model="activityForm" :rules="activityRules" label-width="100px">
        <el-form-item label="活动名称" prop="title">
          <el-input v-model="activityForm.title" placeholder="请输入活动名称" />
        </el-form-item>
        <el-form-item label="开始日期" prop="startDate">
          <el-date-picker v-model="activityForm.startDate" type="date" placeholder="选择开始日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期" prop="endDate">
          <el-date-picker v-model="activityForm.endDate" type="date" placeholder="选择结束日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="上下线状态">
          <el-radio-group v-model="activityForm.status">
            <el-radio :label="1">上线</el-radio>
            <el-radio :label="0">下线</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="activityDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveActivity">确定</el-button>
      </template>
    </el-dialog>

    <!-- ========== 时段弹窗 ========== -->
    <el-dialog v-model="sessionDialogVisible" :title="sessionDialogTitle" width="500px" destroy-on-close>
      <el-form ref="sessionFormRef" :model="sessionForm" :rules="sessionRules" label-width="100px">
        <el-form-item label="时段名称" prop="name">
          <el-input v-model="sessionForm.name" placeholder="如：08:00场" />
        </el-form-item>
        <el-form-item label="开始时间" prop="startTime">
          <el-time-picker v-model="sessionForm.startTime" placeholder="选择开始时间" value-format="HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="endTime">
          <el-time-picker v-model="sessionForm.endTime" placeholder="选择结束时间" value-format="HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-radio-group v-model="sessionForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sessionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSession">确定</el-button>
      </template>
    </el-dialog>

    <!-- ========== 商品弹窗 ========== -->
    <el-dialog v-model="productDialogVisible" :title="productDialogTitle" width="560px" destroy-on-close>
      <el-form ref="productFormRef" :model="productForm" :rules="productRules" label-width="120px">
        <el-form-item label="选择活动" prop="flashPromotionId">
          <el-select v-model="productForm.flashPromotionId" placeholder="选择秒杀活动" style="width: 100%">
            <el-option v-for="item in activityList" :key="item.id" :label="item.title" :value="item.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择时段" prop="flashPromotionSessionId">
          <el-select v-model="productForm.flashPromotionSessionId" placeholder="秒杀时段" style="width: 100%">
            <el-option v-for="item in sessionList" :key="item.id" :label="item.name" :value="item.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品名称" prop="productName">
          <el-input v-model="productForm.productName" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="商品原价">
          <el-input-number v-model="productForm.productPrice" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="秒杀价格" prop="flashPromotionPrice">
          <el-input-number v-model="productForm.flashPromotionPrice" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="秒杀数量" prop="flashPromotionCount">
          <el-input-number v-model="productForm.flashPromotionCount" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="每人限购" prop="flashPromotionLimit">
          <el-input-number v-model="productForm.flashPromotionLimit" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="productForm.sort" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="productDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveProduct">确定</el-button>
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
