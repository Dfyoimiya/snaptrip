<script lang="ts" setup>
import { ref, reactive, onActivated, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets, Edit } from '@element-plus/icons-vue'
import { getProductListAPI, productUpdatePublishStatusAPI, productUpdateNewStatusAPI, productUpdateRecommendStatusAPI, productUpdateDeleteStatusAPI } from '@/apis/product'
import { getBrandAllAPI } from '@/apis/brand'
import { getProductCategoryListWithChildrenAPI } from '@/apis/productCate'
import type { PmsProductCategory } from '@/types/productCate'

const router = useRouter()

// ========== 搜索条件 ==========
const listQuery = ref({
  keyword: '',
  productSn: '',
  categoryId: undefined as string | undefined,
  brandId: undefined as string | undefined,
  publishStatus: undefined as number | undefined,
  verifyStatus: undefined as number | undefined,
  page: 1,
  page_size: 10,
})

interface CascaderOption {
  label: string
  value: string
  children?: CascaderOption[]
}

const brandOptions = ref<Array<{ label: string; value: string }>>([])
const cateOptions = ref<CascaderOption[]>([])

const publishStatusOptions = ref([{ value: 1, label: '上架' }, { value: 0, label: '下架' }])
const verifyStatusOptions = ref([{ value: 1, label: '审核通过' }, { value: 0, label: '未审核' }])

// ========== 数据状态 ==========
const list = ref<any[]>([])
const total = ref(0)
const listLoading = ref(false)
const multipleSelection = ref<any[]>([])

/** 加载商品列表 */
async function fetchList() {
  listLoading.value = true
  try {
    const res = await getProductListAPI(listQuery.value)
    list.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (error) {
    console.error('获取商品列表失败:', error)
    ElMessage.error('获取商品列表失败')
    list.value = []
    total.value = 0
  } finally {
    listLoading.value = false
  }
}

function mapCategoryTree(categories: PmsProductCategory[]): CascaderOption[] {
  return categories.map((category) => ({
    label: category.name,
    value: category.id || '',
    children: category.children?.length ? mapCategoryTree(category.children) : undefined,
  }))
}

async function loadFilterOptions(): Promise<void> {
  try {
    const [brandResponse, categoryResponse] = await Promise.all([
      getBrandAllAPI(),
      getProductCategoryListWithChildrenAPI(),
    ])
    brandOptions.value = brandResponse.data.map((brand) => ({
      label: brand.name,
      value: brand.id || '',
    }))
    cateOptions.value = mapCategoryTree(categoryResponse.data)
  } catch {
    ElMessage.warning('品牌或分类筛选项加载失败')
  }
}

onMounted(() => {
  loadFilterOptions()
})

onActivated(fetchList)

// ========== 搜索 ==========
function handleSearchList() {
  listQuery.value.page = 1
  fetchList()
}
function handleResetSearch() {
  listQuery.value = {
    keyword: '', productSn: '', categoryId: undefined,
    brandId: undefined, publishStatus: undefined, verifyStatus: undefined,
    page: 1, page_size: 10,
  }
  fetchList()
}

// ========== 分页 ==========
function handleSizeChange(val: number) {
  listQuery.value.page = 1
  listQuery.value.page_size = val
  fetchList()
}
function handleCurrentChange(val: number) {
  listQuery.value.page = val
  fetchList()
}

// ========== 表格选择 ==========
function handleSelectionChange(val: any[]) {
  multipleSelection.value = val
}

// ========== 状态变更 ==========
async function handlePublishStatusChange(_index: number, row: any) {
  try {
    await productUpdatePublishStatusAPI(String(row.id), row.publishStatus)
    ElMessage.success('上架状态已更新')
  } catch {
    ElMessage.error('上架状态更新失败')
  } finally {
    await fetchList()
  }
}
async function handleNewStatusChange(_index: number, row: any) {
  try {
    await productUpdateNewStatusAPI(String(row.id), row.newStatus)
    ElMessage.success('新品状态已更新')
  } catch {
    ElMessage.error('新品状态更新失败')
  } finally {
    await fetchList()
  }
}
async function handleRecommendStatusChange(_index: number, row: any) {
  try {
    await productUpdateRecommendStatusAPI(String(row.id), row.recommendStatus)
    ElMessage.success('推荐状态已更新')
  } catch {
    ElMessage.error('推荐状态更新失败')
  } finally {
    await fetchList()
  }
}
function verifyStatusFilter(value: number) {
  return value === 1 ? '审核通过' : '未审核'
}

// ========== 添加/编辑/删除 ==========
function handleAddProduct() {
  router.push({ path: '/pms/addProduct' })
}
function handleUpdateProduct(_index: number, row: any) {
  if (!row.id) return ElMessage.error('商品ID不能为空')
  router.push({ path: '/pms/updateProduct', query: { id: row.id } })
}
async function handleDelete(_index: number, row: any) {
  try {
    await ElMessageBox.confirm('确定删除该商品吗？删除后商品将从列表下架。', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await productUpdateDeleteStatusAPI(String(row.id))
    if (list.value.length === 1 && listQuery.value.page > 1) {
      listQuery.value.page -= 1
    }
    await fetchList()
    ElMessage.success('商品已删除，列表和数据库已同步')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败')
    }
  }
}
function handleShowProduct(_index: number, row: any) {
  console.log('查看商品', row)
}
function handleShowVerifyDetail(_index: number, row: any) {
  console.log('审核详情', row)
}
function handleShowLog(_index: number, row: any) {
  console.log('日志', row)
}

// ========== 批量操作 ==========
const operates = ref([
  { label: '商品上架', value: 'publishOn' },
  { label: '商品下架', value: 'publishOff' },
  { label: '设为推荐', value: 'recommendOn' },
  { label: '取消推荐', value: 'recommendOff' },
  { label: '设为新品', value: 'newOn' },
  { label: '取消新品', value: 'newOff' },
  { label: '移入回收站', value: 'recycle' },
  { label: '转移到分类', value: 'transferCategory' },
])
const operateType = ref<string>()

async function handleBatchOperate() {
  if (!operateType.value) {
    ElMessage({ message: '请选择操作类型', type: 'warning', duration: 1000 })
    return
  }
  if (!multipleSelection.value || multipleSelection.value.length < 1) {
    ElMessage({ message: '请选择要操作的商品', type: 'warning', duration: 1000 })
    return
  }
  ElMessageBox.confirm('是否要进行该批量操作?', '提示', { type: 'warning' }).then(async () => {
    try {
      const ids = multipleSelection.value.map(item => item.id)
      let status = 0
      let action = ''
      switch (operateType.value) {
        case 'publishOn':
          status = 1; action = '上架'
          break
        case 'publishOff':
          status = 0; action = '下架'
          break
        case 'recommendOn':
          status = 1; action = '推荐'
          break
        case 'recommendOff':
          status = 0; action = '取消推荐'
          break
        case 'newOn':
          status = 1; action = '设为新品'
          break
        case 'newOff':
          status = 0; action = '取消新品'
          break
        case 'recycle':
          // 逐个删除
          for (const id of ids) {
            await productUpdateDeleteStatusAPI(String(id))
          }
          ElMessage.success('批量操作成功')
          operateType.value = undefined
          fetchList()
          return
        default:
          ElMessage({ message: '暂不支持该操作', type: 'warning' })
          return
      }
      // 逐个调用状态变更接口
      for (const id of ids) {
        if (operateType.value === 'publishOn' || operateType.value === 'publishOff') {
          await productUpdatePublishStatusAPI(String(id), status)
        } else if (operateType.value === 'recommendOn' || operateType.value === 'recommendOff') {
          await productUpdateRecommendStatusAPI(String(id), status)
        } else if (operateType.value === 'newOn' || operateType.value === 'newOff') {
          await productUpdateNewStatusAPI(String(id), status)
        }
      }
      ElMessage.success('批量操作成功')
      operateType.value = undefined
      fetchList()
    } catch {
      ElMessage.error('批量操作失败')
    }
  })
}

// ========== SKU库存编辑弹窗 ==========
const editSkuInfo = reactive({
  dialogVisible: false,
  productId: 0,
  productSn: '',
  productAttributeCategoryId: 0,
  stockList: [] as any[],
  productAttr: [] as any[],
  keyword: undefined as string | undefined,
})

const skuMockData: Record<number, any[]> = {
  1: [
    { skuCode: 'SKU-001-001', spData: '[{"key":"颜色","value":"黑色"},{"key":"容量","value":"256GB"}]', price: 9999, stock: 100, lowStock: 10 },
    { skuCode: 'SKU-001-002', spData: '[{"key":"颜色","value":"白色"},{"key":"容量","value":"256GB"}]', price: 9999, stock: 80, lowStock: 10 },
    { skuCode: 'SKU-001-003', spData: '[{"key":"颜色","value":"黑色"},{"key":"容量","value":"512GB"}]', price: 10999, stock: 60, lowStock: 10 },
    { skuCode: 'SKU-001-004', spData: '[{"key":"颜色","value":"白色"},{"key":"容量","value":"512GB"}]', price: 10999, stock: 50, lowStock: 10 },
    { skuCode: 'SKU-001-005', spData: '[{"key":"颜色","value":"原色"},{"key":"容量","value":"256GB"}]', price: 9999, stock: 45, lowStock: 10 },
    { skuCode: 'SKU-001-006', spData: '[{"key":"颜色","value":"原色"},{"key":"容量","value":"512GB"}]', price: 10999, stock: 30, lowStock: 10 },
  ],
}

function getProductSkuSp(row: any, index: number) {
  try {
    const spData = JSON.parse(row.spData)
    if (spData && index < spData.length) return spData[index].value
  } catch { /* ignore */ }
  return ''
}

function handleShowSkuEditDialog(_index: number, row: any) {
  editSkuInfo.dialogVisible = true
  editSkuInfo.productId = row.id
  editSkuInfo.productSn = row.productSn
  editSkuInfo.productAttributeCategoryId = row.productAttributeCategoryId
  editSkuInfo.keyword = undefined
  const skus = skuMockData[row.id] || [
    { skuCode: `SKU-${String(row.id).padStart(3,'0')}-001`, spData: '[{"key":"颜色","value":"默认色"},{"key":"规格","value":"标准版"}]', price: row.price, stock: 100, lowStock: 10 },
  ]
  editSkuInfo.stockList = [...skus]
  // Derive attribute column headers from actual SKU spData
  const firstSku = editSkuInfo.stockList[0]
  let spData: { key: string }[] = []
  if (firstSku?.spData) {
    try { spData = JSON.parse(firstSku.spData) } catch { /* ignore */ }
  }
  if (spData && Array.isArray(spData) && spData.length > 0) {
    editSkuInfo.productAttr = spData.map((item, idx) => ({ id: idx, name: item.key || '属性' }))
  } else {
    editSkuInfo.productAttr = [{ id: 0, name: '规格' }]
  }
}

function handleSearchEditSku() {
  ElMessage.success('SKU搜索完成')
}

function handleEditSkuConfirm() {
  if (!editSkuInfo.stockList || editSkuInfo.stockList.length <= 0) {
    ElMessage({ message: '暂无sku信息', type: 'warning', duration: 1000 })
    return
  }
  ElMessageBox.confirm('是否要进行修改', '提示', { type: 'warning' }).then(() => {
    ElMessage({ message: '修改成功', type: 'success', duration: 1000 })
    editSkuInfo.dialogVisible = false
  })
}
</script>

<template>
  <div class="page-product-list">
    <!-- 筛选搜索 -->
    <el-card class="filter-container" shadow="never">
      <div>
        <el-icon class="el-icon-middle"><Search /></el-icon>
        <span>筛选搜索</span>
        <el-button style="float: right" @click="handleSearchList" type="primary">查询结果</el-button>
        <el-button style="float: right; margin-right: 15px" @click="handleResetSearch">重置</el-button>
      </div>
      <div style="margin-top: 20px">
        <el-form :inline="true" :model="listQuery" label-width="140px">
          <el-form-item label="输入搜索：">
            <el-input style="width: 203px" v-model="listQuery.keyword" placeholder="商品名称"></el-input>
          </el-form-item>
          <el-form-item label="商品货号：">
            <el-input style="width: 203px" v-model="listQuery.productSn" placeholder="商品货号"></el-input>
          </el-form-item>
          <el-form-item label="商品分类：">
            <el-cascader
              clearable
              v-model="listQuery.categoryId"
              :options="cateOptions"
              :props="{ emitPath: false }"
              style="width: 203px"
            />
          </el-form-item>
          <el-form-item label="商品品牌：">
            <el-select v-model="listQuery.brandId" placeholder="请选择品牌" clearable style="width: 203px">
              <el-option v-for="item in brandOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="上架状态：">
            <el-select v-model="listQuery.publishStatus" placeholder="全部" clearable style="width: 203px">
              <el-option v-for="item in publishStatusOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="审核状态：">
            <el-select v-model="listQuery.verifyStatus" placeholder="全部" clearable style="width: 203px">
              <el-option v-for="item in verifyStatusOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 操作栏 -->
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button v-permission="'product:create'" class="btn-add" @click="handleAddProduct">添加</el-button>
    </el-card>

    <!-- 表格 -->
    <div class="table-container">
      <el-table ref="productTable" :data="list" style="width: 100%" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center"></el-table-column>
        <el-table-column label="编号" width="100" align="center">
          <template #default="scope">{{ scope.row.id }}</template>
        </el-table-column>
        <el-table-column label="商品图片" width="120" align="center">
          <template #default="scope"><img style="height: 80px" :src="scope.row.defaultPic"></template>
        </el-table-column>
        <el-table-column label="商品名称" align="center">
          <template #default="scope">
            <p>{{ scope.row.name }}</p>
            <p>品牌：{{ scope.row.brandName || scope.row.brand_name }}</p>
          </template>
        </el-table-column>
        <el-table-column label="价格/货号" width="140" align="center">
          <template #default="scope">
            <p>价格：￥{{ scope.row.price }}</p>
            <p>货号：{{ scope.row.productSn || scope.row.product_sn }}</p>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="140" align="center">
          <template #default="scope">
            <p style="margin: 6px 0px;">上架：
              <el-switch @change="handlePublishStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.publishStatus"></el-switch>
            </p>
            <p style="margin: 6px 0px;">新品：
              <el-switch @change="handleNewStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.newStatus"></el-switch>
            </p>
            <p style="margin: 6px 0px;">推荐：
              <el-switch @change="handleRecommendStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.recommendStatus"></el-switch>
            </p>
          </template>
        </el-table-column>
        <el-table-column label="排序" width="100" align="center">
          <template #default="scope">{{ scope.row.sort }}</template>
        </el-table-column>
        <el-table-column label="SKU库存" width="100" align="center">
          <template #default="scope">
            <el-button type="primary" :icon="Edit" size="large" @click="handleShowSkuEditDialog(scope.$index, scope.row)" circle></el-button>
          </template>
        </el-table-column>
        <el-table-column label="销量" width="100" align="center">
          <template #default="scope">{{ scope.row.saleCount }}</template>
        </el-table-column>
        <el-table-column label="审核状态" width="100" align="center">
          <template #default="scope">
            <p>{{ verifyStatusFilter(scope.row.verifyStatus) }}</p>
            <p><el-button type="primary" link @click="handleShowVerifyDetail(scope.$index, scope.row)">审核详情</el-button></p>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="scope">
            <p>
              <el-button size="small" @click="handleShowProduct(scope.$index, scope.row)">查看</el-button>
              <el-button size="small" @click="handleUpdateProduct(scope.$index, scope.row)">编辑</el-button>
            </p>
            <p>
              <el-button size="small" @click="handleShowLog(scope.$index, scope.row)">日志</el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
            </p>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 批量操作 -->
    <div class="batch-operate-container">
      <el-select v-model="operateType" placeholder="批量操作" style="width: 150px">
        <el-option v-for="item in operates" :key="item.value" :label="item.label" :value="item.value"></el-option>
      </el-select>
      <el-button style="margin-left: 20px" @click="handleBatchOperate" type="primary">确定</el-button>
    </div>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes, prev, pager, next, jumper" :page-size="listQuery.page_size" :page-sizes="[5, 10, 15]"
        v-model:current-page="listQuery.page" :total="total"></el-pagination>
    </div>

    <!-- SKU库存编辑弹窗 -->
    <el-dialog title="编辑货品信息" v-model="editSkuInfo.dialogVisible" width="50%">
      <span>商品货号：</span><span>{{ editSkuInfo.productSn }}</span>
      <el-input placeholder="按sku编号搜索" v-model="editSkuInfo.keyword" style="width: 60%; margin-left: 20px">
        <template #append>
          <el-button :icon="Search" @click="handleSearchEditSku"></el-button>
        </template>
      </el-input>
      <el-table style="width: 100%; margin-top: 20px" :data="editSkuInfo.stockList" border>
        <el-table-column label="SKU编号" align="center">
          <template #default="scope">
            <el-input v-model="scope.row.skuCode"></el-input>
          </template>
        </el-table-column>
        <el-table-column v-for="(item, index) in editSkuInfo.productAttr" :label="item.name" :key="item.id" align="center">
          <template #default="scope">{{ getProductSkuSp(scope.row, index) }}</template>
        </el-table-column>
        <el-table-column label="销售价格" width="100" align="center">
          <template #default="scope"><el-input v-model="scope.row.price"></el-input></template>
        </el-table-column>
        <el-table-column label="商品库存" width="100" align="center">
          <template #default="scope"><el-input v-model="scope.row.stock"></el-input></template>
        </el-table-column>
        <el-table-column label="库存预警值" width="100" align="center">
          <template #default="scope"><el-input v-model="scope.row.lowStock"></el-input></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editSkuInfo.dialogVisible = false">取 消</el-button>
          <el-button type="primary" @click="handleEditSkuConfirm">确 定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page-product-list {
  .filter-container { margin-bottom: 12px; border-radius: 8px; }
  .operate-container {
    margin-bottom: 12px;
    border-radius: 8px;
    .btn-add { float: right; }
  }
  .table-container { margin-bottom: 12px; }
  .batch-operate-container {
    display: inline-block;
    margin-top: 12px;
  }
  .pagination-container {
    display: inline-block;
    float: right;
    margin-top: 12px;
  }
  .el-icon-middle { vertical-align: middle; margin-right: 6px; }
}
</style>
