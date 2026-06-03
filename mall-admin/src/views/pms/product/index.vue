<script lang="ts" setup>
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Tickets, Edit } from '@element-plus/icons-vue'

const router = useRouter()

// ========== 搜索条件 ==========
const listQuery = ref({
  keyword: '',
  productSn: '',
  productCategoryId: undefined as number | undefined,
  brandId: undefined as number | undefined,
  publishStatus: undefined as number | undefined,
  verifyStatus: undefined as number | undefined,
  pageNum: 1,
  pageSize: 10,
})

const brandOptions = ref([
  { label: 'Apple', value: 1 },
  { label: '华为', value: 2 },
  { label: '小米', value: 3 },
  { label: 'Nike', value: 4 },
  { label: 'Adidas', value: 5 },
  { label: '索尼', value: 6 },
])

const cateOptions = ref([
  { label: '手机数码', value: 1, children: [
    { label: '手机', value: 11 },
    { label: '平板电脑', value: 12 },
    { label: '智能手表', value: 13 },
  ]},
  { label: '电脑办公', value: 2, children: [
    { label: '笔记本电脑', value: 21 },
    { label: '台式机', value: 22 },
    { label: '显示器', value: 23 },
  ]},
  { label: '服装鞋包', value: 3, children: [
    { label: '男装', value: 31 },
    { label: '女装', value: 32 },
    { label: '运动鞋', value: 33 },
  ]},
])

const publishStatusOptions = ref([{ value: 1, label: '上架' }, { value: 0, label: '下架' }])
const verifyStatusOptions = ref([{ value: 1, label: '审核通过' }, { value: 0, label: '未审核' }])

// ========== 原始数据 ==========
const allData = ref([
  { id: 1, pic: 'https://picsum.photos/seed/iphone/200/200', name: 'iPhone 15 Pro Max', productSn: 'APP-2024-001', brandName: 'Apple', productCategoryName: '手机', productAttributeCategoryId: 1, price: 9999, publishStatus: 1, newStatus: 1, recommandStatus: 1, sort: 100, sale: 528, verifyStatus: 1 },
  { id: 2, pic: 'https://picsum.photos/seed/huawei/200/200', name: '华为 Mate 60 Pro', productSn: 'HW-2024-002', brandName: '华为', productCategoryName: '手机', productAttributeCategoryId: 1, price: 6999, publishStatus: 1, newStatus: 1, recommandStatus: 0, sort: 99, sale: 1024, verifyStatus: 1 },
  { id: 3, pic: 'https://picsum.photos/seed/mi14/200/200', name: '小米14 Ultra', productSn: 'XM-2024-003', brandName: '小米', productCategoryName: '手机', productAttributeCategoryId: 1, price: 5999, publishStatus: 1, newStatus: 0, recommandStatus: 1, sort: 98, sale: 896, verifyStatus: 1 },
  { id: 4, pic: 'https://picsum.photos/seed/macbook/200/200', name: 'MacBook Pro 14英寸', productSn: 'APP-2024-004', brandName: 'Apple', productCategoryName: '笔记本电脑', productAttributeCategoryId: 2, price: 14999, publishStatus: 1, newStatus: 0, recommandStatus: 0, sort: 97, sale: 234, verifyStatus: 1 },
  { id: 5, pic: 'https://picsum.photos/seed/airpods/200/200', name: 'AirPods Pro 2', productSn: 'APP-2024-005', brandName: 'Apple', productCategoryName: '手机配件', productAttributeCategoryId: 1, price: 1899, publishStatus: 0, newStatus: 0, recommandStatus: 1, sort: 96, sale: 3456, verifyStatus: 0 },
  { id: 6, pic: 'https://picsum.photos/seed/gt4/200/200', name: '华为 Watch GT 4', productSn: 'HW-2024-006', brandName: '华为', productCategoryName: '智能手表', productAttributeCategoryId: 1, price: 1488, publishStatus: 1, newStatus: 1, recommandStatus: 1, sort: 95, sale: 678, verifyStatus: 1 },
  { id: 7, pic: 'https://picsum.photos/seed/ipad/200/200', name: 'iPad Air 5', productSn: 'APP-2024-007', brandName: 'Apple', productCategoryName: '平板电脑', productAttributeCategoryId: 1, price: 4799, publishStatus: 1, newStatus: 0, recommandStatus: 0, sort: 94, sale: 432, verifyStatus: 1 },
  { id: 8, pic: 'https://picsum.photos/seed/miband/200/200', name: '小米手环8 Pro', productSn: 'XM-2024-008', brandName: '小米', productCategoryName: '智能手表', productAttributeCategoryId: 1, price: 399, publishStatus: 1, newStatus: 1, recommandStatus: 1, sort: 93, sale: 5678, verifyStatus: 1 },
  { id: 9, pic: 'https://picsum.photos/seed/nike/200/200', name: 'Nike Air Max', productSn: 'NK-2024-009', brandName: 'Nike', productCategoryName: '运动鞋', productAttributeCategoryId: 4, price: 899, publishStatus: 1, newStatus: 0, recommandStatus: 0, sort: 92, sale: 3456, verifyStatus: 1 },
  { id: 10, pic: 'https://picsum.photos/seed/adidas/200/200', name: 'Adidas Ultraboost', productSn: 'AD-2024-010', brandName: 'Adidas', productCategoryName: '运动鞋', productAttributeCategoryId: 4, price: 1299, publishStatus: 1, newStatus: 1, recommandStatus: 1, sort: 91, sale: 2100, verifyStatus: 1 },
])

// ========== 筛选逻辑 ==========
const filteredList = computed(() => {
  return allData.value.filter((item) => {
    if (listQuery.value.keyword && !item.name.includes(listQuery.value.keyword)) return false
    if (listQuery.value.productSn && !item.productSn.includes(listQuery.value.productSn)) return false
    if (listQuery.value.brandId && item.brandName !== brandOptions.value.find(b => b.value === listQuery.value.brandId)?.label) return false
    if (listQuery.value.publishStatus !== undefined && item.publishStatus !== listQuery.value.publishStatus) return false
    if (listQuery.value.verifyStatus !== undefined && item.verifyStatus !== listQuery.value.verifyStatus) return false
    return true
  })
})

const list = computed(() => {
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  return filteredList.value.slice(start, start + listQuery.value.pageSize)
})

const total = computed(() => filteredList.value.length)
const listLoading = ref(false)
const multipleSelection = ref<any[]>([])

// ========== 搜索 ==========
function handleSearchList() {
  listQuery.value.pageNum = 1
}
function handleResetSearch() {
  listQuery.value = {
    keyword: '', productSn: '', productCategoryId: undefined,
    brandId: undefined, publishStatus: undefined, verifyStatus: undefined,
    pageNum: 1, pageSize: 10,
  }
}

// ========== 分页 ==========
function handleSizeChange(val: number) {
  listQuery.value.pageNum = 1
  listQuery.value.pageSize = val
}
function handleCurrentChange(val: number) {
  listQuery.value.pageNum = val
}

// ========== 表格选择 ==========
function handleSelectionChange(val: any[]) {
  multipleSelection.value = val
}

// ========== 状态变更 ==========
function handlePublishStatusChange(_index: number, row: any) {
  ElMessage.success('上架状态已更新')
}
function handleNewStatusChange(_index: number, row: any) {
  ElMessage.success('新品状态已更新')
}
function handleRecommendStatusChange(_index: number, row: any) {
  ElMessage.success('推荐状态已更新')
}
function verifyStatusFilter(value: number) {
  return value === 1 ? '审核通过' : '未审核'
}

// ========== 添加/编辑/删除 ==========
function handleAddProduct() {
  router.push({ path: '/pms/addProduct' })
}
function handleUpdateProduct(_index: number, row: any) {
  router.push({ path: '/pms/updateProduct', query: { id: row.id } })
}
function handleDelete(_index: number, row: any) {
  ElMessageBox.confirm('是否要进行删除操作?', '提示', { type: 'warning' }).then(() => {
    allData.value = allData.value.filter(item => item.id !== row.id)
    ElMessage.success('删除成功')
  })
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

function handleBatchOperate() {
  if (!operateType.value) {
    ElMessage({ message: '请选择操作类型', type: 'warning', duration: 1000 })
    return
  }
  if (!multipleSelection.value || multipleSelection.value.length < 1) {
    ElMessage({ message: '请选择要操作的商品', type: 'warning', duration: 1000 })
    return
  }
  ElMessageBox.confirm('是否要进行该批量操作?', '提示', { type: 'warning' }).then(() => {
    const ids = multipleSelection.value.map(item => item.id)
    switch (operateType.value) {
      case 'publishOn':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.publishStatus = 1)
        break
      case 'publishOff':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.publishStatus = 0)
        break
      case 'recommendOn':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.recommandStatus = 1)
        break
      case 'recommendOff':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.recommandStatus = 0)
        break
      case 'newOn':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.newStatus = 1)
        break
      case 'newOff':
        allData.value.filter(item => ids.includes(item.id)).forEach(item => item.newStatus = 0)
        break
      case 'recycle':
        allData.value = allData.value.filter(item => !ids.includes(item.id))
        break
    }
    ElMessage.success('批量操作成功')
    operateType.value = undefined
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
  // 模拟SKU数据
  const skus = skuMockData[row.id] || [
    { skuCode: `SKU-${String(row.id).padStart(3,'0')}-001`, spData: '[{"key":"颜色","value":"默认色"},{"key":"规格","value":"标准版"}]', price: row.price, stock: 100, lowStock: 10 },
  ]
  editSkuInfo.stockList = [...skus]
  // 模拟属性列
  if (row.productAttributeCategoryId === 1) {
    editSkuInfo.productAttr = [{ id: 1, name: '颜色' }, { id: 2, name: '容量' }]
  } else if (row.productAttributeCategoryId === 4) {
    editSkuInfo.productAttr = [{ id: 1, name: '颜色' }, { id: 2, name: '尺码' }]
  } else {
    editSkuInfo.productAttr = [{ id: 1, name: '规格' }]
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
            <el-cascader clearable v-model="listQuery.productCategoryId" :options="cateOptions" style="width: 203px"></el-cascader>
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
      <el-button class="btn-add" @click="handleAddProduct">添加</el-button>
    </el-card>

    <!-- 表格 -->
    <div class="table-container">
      <el-table ref="productTable" :data="list" style="width: 100%" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center"></el-table-column>
        <el-table-column label="编号" width="100" align="center">
          <template #default="scope">{{ scope.row.id }}</template>
        </el-table-column>
        <el-table-column label="商品图片" width="120" align="center">
          <template #default="scope"><img style="height: 80px" :src="scope.row.pic"></template>
        </el-table-column>
        <el-table-column label="商品名称" align="center">
          <template #default="scope">
            <p>{{ scope.row.name }}</p>
            <p>品牌：{{ scope.row.brandName }}</p>
          </template>
        </el-table-column>
        <el-table-column label="价格/货号" width="140" align="center">
          <template #default="scope">
            <p>价格：￥{{ scope.row.price }}</p>
            <p>货号：{{ scope.row.productSn }}</p>
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
              <el-switch @change="handleRecommendStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0" v-model="scope.row.recommandStatus"></el-switch>
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
          <template #default="scope">{{ scope.row.sale }}</template>
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
        layout="total, sizes, prev, pager, next, jumper" :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]"
        v-model:current-page="listQuery.pageNum" :total="total"></el-pagination>
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
