<script setup lang="ts">
import { reactive, computed, inject, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['prev-step', 'next-step'])

const compProductParam = inject('product-key') as Ref<any>

const state = reactive({
  productAttributeCategoryOptions: [
    { label: '手机属性', value: 1 },
    { label: '电脑属性', value: 2 },
    { label: '服装属性', value: 3 },
    { label: '鞋靴属性', value: 4 },
  ],
  selectProductAttr: [] as any[],
  selectProductParam: [] as any[],
  selectProductAttrPics: [] as any[],
  addProductAttrValue: '',
  activeHtmlName: 'pc',
})

const hasAttrPic = computed(() => state.selectProductAttrPics.length >= 1)

// 商品主图和画册
const selectProductPics = computed({
  get() {
    const pics: string[] = []
    if (compProductParam.value.pic) pics.push(compProductParam.value.pic)
    if (compProductParam.value.albumPics) {
      pics.push(...compProductParam.value.albumPics.split(','))
    }
    return pics
  },
  set(newValue: string[]) {
    if (!newValue || newValue.length === 0) {
      compProductParam.value.pic = ''
      compProductParam.value.albumPics = ''
    } else {
      compProductParam.value.pic = newValue[0]
      compProductParam.value.albumPics = newValue.slice(1).join(',')
    }
  }
})

const handleProductAttrChange = (value: number) => {
  // 模拟根据属性分类ID获取规格和参数
  if (value === 1) { // 手机属性
    state.selectProductAttr = [
      { id: 1, name: '颜色', handAddStatus: 0, inputList: '黑色,白色,蓝色,金色,原色', values: [] },
      { id: 2, name: '容量', handAddStatus: 0, inputList: '128GB,256GB,512GB,1TB', values: [] },
    ]
    state.selectProductParam = [
      { id: 3, name: '屏幕尺寸', value: '', inputType: 1, inputList: '6.1英寸,6.7英寸' },
      { id: 4, name: '网络类型', value: '', inputType: 1, inputList: '5G,4G' },
      { id: 5, name: '电池容量', value: '', inputType: 0, inputList: '' },
    ]
  } else if (value === 2) { // 电脑属性
    state.selectProductAttr = [
      { id: 6, name: '颜色', handAddStatus: 0, inputList: '银色,深空灰', values: [] },
      { id: 7, name: '内存', handAddStatus: 0, inputList: '8GB,16GB,32GB', values: [] },
    ]
    state.selectProductParam = [
      { id: 8, name: '处理器', value: '', inputType: 0, inputList: '' },
      { id: 9, name: '硬盘容量', value: '', inputType: 1, inputList: '256GB,512GB,1TB' },
    ]
  } else {
    state.selectProductAttr = [
      { id: 10, name: '颜色', handAddStatus: 0, inputList: '黑色,白色,红色', values: [] },
    ]
    state.selectProductParam = [
      { id: 11, name: '尺码', value: '', inputType: 1, inputList: 'S,M,L,XL' },
    ]
  }
  state.selectProductAttrPics = []
  compProductParam.value.skuStockList = []
}

const getInputListArr = (inputList: string) => inputList ? inputList.split(',') : []

const handleAddProductAttrValue = (idx: number) => {
  const attr = state.selectProductAttr[idx]
  if (!state.addProductAttrValue) {
    ElMessage({ message: '属性值不能为空', type: 'warning', duration: 1000 })
    return
  }
  if (!attr.options) attr.options = []
  if (attr.options.indexOf(state.addProductAttrValue) !== -1) {
    ElMessage({ message: '属性值不能重复', type: 'warning', duration: 1000 })
    return
  }
  attr.options.push(state.addProductAttrValue)
  state.addProductAttrValue = ''
}

const handleRemoveProductAttrValue = (idx: number, index: number) => {
  state.selectProductAttr[idx]?.options?.splice(index, 1)
}

const getProductSkuSp = (row: any, index: number) => {
  try {
    const spData = JSON.parse(row.spData)
    if (spData && index < spData.length) return spData[index].value
  } catch { /* ignore */ }
  return null
}

const handleRefreshProductSkuList = async () => {
  await ElMessageBox.confirm('刷新列表将导致sku信息重新生成，是否要刷新', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  })
  refreshProductSkuList()
  refreshProductAttrPics()
}

const handleSyncProductSkuPrice = async () => {
  await ElMessageBox.confirm('将同步第一个sku的价格到所有sku,是否继续', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  })
  const list = compProductParam.value.skuStockList
  if (list && list.length > 0) {
    const price = list[0].price
    list.forEach((item: any) => item.price = price)
  }
}

const handleSyncProductSkuStock = async () => {
  await ElMessageBox.confirm('将同步第一个sku的库存到所有sku,是否继续', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  })
  const list = compProductParam.value.skuStockList
  if (list && list.length > 0) {
    const stock = list[0].stock
    const lowStock = list[0].lowStock
    list.forEach((item: any) => { item.stock = stock; item.lowStock = lowStock })
  }
}

const refreshProductSkuList = () => {
  const skuList: any[] = []
  if (state.selectProductAttr.length === 1) {
    const attr = state.selectProductAttr[0]
    for (let i = 0; i < attr.values.length; i++) {
      skuList.push({ spData: JSON.stringify([{ key: attr.name, value: attr.values[i] }]), price: 0, promotionPrice: 0, stock: 0, lowStock: 0, skuCode: '' })
    }
  } else if (state.selectProductAttr.length === 2) {
    const a0 = state.selectProductAttr[0], a1 = state.selectProductAttr[1]
    for (let i = 0; i < a0.values.length; i++) {
      if (a1.values.length === 0) { skuList.push({ spData: JSON.stringify([{ key: a0.name, value: a0.values[i] }]) }); continue }
      for (let j = 0; j < a1.values.length; j++) {
        skuList.push({ spData: JSON.stringify([{ key: a0.name, value: a0.values[i] }, { key: a1.name, value: a1.values[j] }]), price: 0, promotionPrice: 0, stock: 0, lowStock: 0, skuCode: '' })
      }
    }
  } else if (state.selectProductAttr.length === 3) {
    const a0 = state.selectProductAttr[0], a1 = state.selectProductAttr[1], a2 = state.selectProductAttr[2]
    for (let i = 0; i < a0.values.length; i++) {
      for (let j = 0; j < a1.values.length; j++) {
        for (let k = 0; k < a2.values.length; k++) {
          skuList.push({ spData: JSON.stringify([{ key: a0.name, value: a0.values[i] }, { key: a1.name, value: a1.values[j] }, { key: a2.name, value: a2.values[k] }]), price: 0, promotionPrice: 0, stock: 0, lowStock: 0, skuCode: '' })
        }
      }
    }
  }
  compProductParam.value.skuStockList = skuList
}

const refreshProductAttrPics = () => {
  state.selectProductAttrPics = []
  if (state.selectProductAttr.length >= 1) {
    const values = state.selectProductAttr[0].values || []
    for (let i = 0; i < values.length; i++) {
      state.selectProductAttrPics.push({ name: values[i], pic: '' })
    }
  }
}

const handleRemoveProductSku = (index: number) => {
  const list = compProductParam.value.skuStockList
  if (list.length === 1) list.pop()
  else list.splice(index, 1)
}

const mergeProductAttrValue = () => {
  compProductParam.value.productAttributeValueList = []
  for (let i = 0; i < state.selectProductAttr.length; i++) {
    const attr = state.selectProductAttr[i]
    if (attr.handAddStatus === 1 && attr.options?.length > 0) {
      compProductParam.value.productAttributeValueList.push({
        productAttributeId: attr.id,
        value: attr.options.join(',')
      })
    }
  }
  for (let i = 0; i < state.selectProductParam.length; i++) {
    const param = state.selectProductParam[i]
    compProductParam.value.productAttributeValueList.push({
      productAttributeId: param.id,
      value: param.value
    })
  }
}

const mergeProductAttrPics = () => {
  for (let i = 0; i < state.selectProductAttrPics.length; i++) {
    const skuList = compProductParam.value.skuStockList
    for (let j = 0; j < skuList.length; j++) {
      const spData = JSON.parse(skuList[j].spData)
      if (spData[0]?.value === state.selectProductAttrPics[i].name) {
        skuList[j].pic = state.selectProductAttrPics[i].pic
      }
    }
  }
}

const handlePrev = () => { emit('prev-step') }
const handleNext = () => { mergeProductAttrValue(); mergeProductAttrPics(); emit('next-step') }
</script>

<template>
  <div style="margin-top: 50px">
    <el-form :model="compProductParam" label-width="120px" class="form-inner-container">
      <el-form-item label="属性类型：">
        <el-select v-model="compProductParam.productAttributeCategoryId" placeholder="请选择属性类型" @change="handleProductAttrChange">
          <el-option v-for="item in state.productAttributeCategoryOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品规格：" v-if="state.selectProductAttr.length > 0">
        <el-card shadow="never" class="cardBg">
          <div v-for="(productAttr, idx) in state.selectProductAttr" :key="'productAttr' + idx">
            {{ productAttr.name }}：
            <el-checkbox-group v-if="productAttr.handAddStatus === 0" v-model="state.selectProductAttr[idx].values">
              <el-checkbox v-for="item in getInputListArr(productAttr.inputList)" :label="item" :key="item" class="littleMarginLeft" />
            </el-checkbox-group>
            <div v-else>
              <el-checkbox-group v-model="state.selectProductAttr[idx].values">
                <div v-for="(item, index) in state.selectProductAttr[idx].options" style="display: inline-flex;" class="littleMarginLeft" :key="'options' + index">
                  <el-checkbox :label="item" :key="item"></el-checkbox>
                  <el-button link type="primary" class="littleMarginLeft" @click="handleRemoveProductAttrValue(idx, index)">删除</el-button>
                </div>
              </el-checkbox-group>
              <el-input v-model="state.addProductAttrValue" style="width: 160px; margin-left: 10px" clearable />
              <el-button class="littleMarginLeft" @click="handleAddProductAttrValue(idx)">增加</el-button>
            </div>
          </div>
        </el-card>
        <el-table style="width: 100%; margin-top: 20px" :data="compProductParam.skuStockList" border v-if="compProductParam.skuStockList.length > 0">
          <el-table-column v-for="(item, index) in state.selectProductAttr" :label="item.name" :key="item.id" align="center">
            <template #default="scope">{{ getProductSkuSp(scope.row, index) }}</template>
          </el-table-column>
          <el-table-column label="销售价格" width="100" align="center">
            <template #default="scope"><el-input v-model="scope.row.price" /></template>
          </el-table-column>
          <el-table-column label="促销价格" width="100" align="center">
            <template #default="scope"><el-input v-model="scope.row.promotionPrice" /></template>
          </el-table-column>
          <el-table-column label="商品库存" width="80" align="center">
            <template #default="scope"><el-input v-model="scope.row.stock" /></template>
          </el-table-column>
          <el-table-column label="库存预警" width="80" align="center">
            <template #default="scope"><el-input v-model="scope.row.lowStock" /></template>
          </el-table-column>
          <el-table-column label="SKU编号" width="160" align="center">
            <template #default="scope"><el-input v-model="scope.row.skuCode" /></template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="scope"><el-button link type="primary" @click="handleRemoveProductSku(scope.$index)">删除</el-button></template>
          </el-table-column>
        </el-table>
        <div v-if="state.selectProductAttr.length > 0" style="margin-top: 10px">
          <el-button type="primary" @click="handleRefreshProductSkuList">刷新列表</el-button>
          <el-button type="primary" @click="handleSyncProductSkuPrice">同步价格</el-button>
          <el-button type="primary" @click="handleSyncProductSkuStock">同步库存</el-button>
        </div>
      </el-form-item>
      <el-form-item label="属性图片：" v-if="hasAttrPic">
        <el-card shadow="never" class="cardBg">
          <div v-for="(item, index) in state.selectProductAttrPics" :key="'productAttrPic' + index">
            <span>{{ item.name }}:</span>
            <el-input v-model="item.pic" style="width: 300px; margin-left: 10px" placeholder="图片URL" />
          </div>
        </el-card>
      </el-form-item>
      <el-form-item label="商品参数：" v-if="state.selectProductParam.length > 0">
        <el-card shadow="never" class="cardBg">
          <div v-for="(item, index) in state.selectProductParam" :class="{ littleMarginTop: index !== 0 }" :key="'productParam' + index">
            <div class="paramInputLabel">{{ item.name }}:</div>
            <el-select v-if="item.inputType === 1" class="paramInput" v-model="state.selectProductParam[index].value">
              <el-option v-for="item2 in getInputListArr(item.inputList)" :key="item2" :label="item2" :value="item2" />
            </el-select>
            <el-input v-else class="paramInput" v-model="state.selectProductParam[index].value" />
          </div>
        </el-card>
      </el-form-item>
      <el-form-item label="商品相册：">
        <el-select-v2 v-model="selectProductPics" multiple filterable allow-create clearable placeholder="输入图片URL按回车添加" :options="[]" style="width: 100%" />
      </el-form-item>
      <el-form-item label="商品详情：">
        <el-tabs v-model="state.activeHtmlName" type="card" style="width: 100%">
          <el-tab-pane label="电脑端详情" name="pc">
            <el-input type="textarea" :rows="10" v-model="compProductParam.detailHtml" placeholder="支持HTML格式" />
          </el-tab-pane>
          <el-tab-pane label="移动端详情" name="mobile">
            <el-input type="textarea" :rows="10" v-model="compProductParam.detailMobileHtml" placeholder="支持HTML格式" />
          </el-tab-pane>
        </el-tabs>
      </el-form-item>
      <el-form-item>
        <div style="width: 100%; text-align: center;">
          <el-button @click="handlePrev">上一步，填写商品促销</el-button>
          <el-button type="primary" @click="handleNext">下一步，选择商品关联</el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.littleMarginLeft { margin-left: 10px; }
.littleMarginTop { margin-top: 10px; }
.paramInput { width: 250px; }
.paramInputLabel { display: inline-block; width: 100px; text-align: right; padding-right: 10px }
.cardBg { background: #F8F9FC; }
</style>
