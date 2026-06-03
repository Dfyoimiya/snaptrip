<script setup lang="ts">
import { ref, onMounted, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProductInfoDetail from './ProductInfoDetail.vue'
import ProductSaleDetail from './ProductSaleDetail.vue'
import ProductAttrDetail from './ProductAttrDetail.vue'
import ProductRelationDetail from './ProductRelationDetail.vue'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})

// 默认商品参数
const defaultProductParam = {
  albumPics: '',
  brandName: '',
  deleteStatus: 0,
  description: '',
  detailDesc: '',
  detailHtml: '',
  detailMobileHtml: '',
  detailTitle: '',
  feightTemplateId: 0,
  flashPromotionCount: 0,
  flashPromotionId: 0,
  flashPromotionPrice: 0,
  flashPromotionSort: 0,
  giftPoint: 0,
  giftGrowth: 0,
  keywords: '',
  lowStock: 0,
  name: '',
  newStatus: 0,
  note: '',
  originalPrice: 0,
  pic: '',
  memberPriceList: [],
  productFullReductionList: [{ fullPrice: 0, reducePrice: 0 }],
  productLadderList: [{ count: 0, discount: 0, price: 0 }],
  previewStatus: 0,
  price: 0,
  productAttributeValueList: [],
  skuStockList: [],
  subjectProductRelationList: [],
  prefrenceAreaProductRelationList: [],
  productCategoryName: '',
  productSn: '',
  promotionEndTime: '',
  promotionPerLimit: 0,
  promotionStartTime: '',
  promotionType: 0,
  publishStatus: 0,
  recommandStatus: 0,
  sale: 0,
  serviceIds: '',
  sort: 0,
  stock: 0,
  subTitle: '',
  unit: '',
  usePointLimit: 0,
  verifyStatus: 0,
  weight: 0,
}

const active = ref(0)
const showStatus = ref([true, false, false, false])
const productParam = ref(Object.assign({}, defaultProductParam))

// 跨层传递数据
provide('product-key', productParam)

onMounted(async () => {
  if (props.isEdit) {
    // 模拟编辑数据
    productParam.value = {
      ...productParam.value,
      name: 'iPhone 15 Pro Max',
      subTitle: '苹果最新旗舰手机',
      brandId: 1,
      brandName: 'Apple',
      productCategoryId: 11,
      productCategoryName: '手机',
      productSn: 'APP-2024-001',
      price: 9999,
      originalPrice: 10999,
      stock: 500,
      unit: '部',
      weight: 200,
      sort: 100,
      description: 'iPhone 15 Pro Max 是苹果最新旗舰手机',
      publishStatus: 1,
      newStatus: 1,
      recommandStatus: 1,
      detailTitle: 'iPhone 15 Pro Max 详情',
      detailDesc: '详细介绍',
      keywords: 'iPhone,苹果,手机',
      note: '备注信息',
      giftPoint: 100,
      giftGrowth: 100,
      usePointLimit: 0,
      serviceIds: '1,2,3',
      pic: 'https://picsum.photos/seed/iphone/200/200',
      albumPics: 'https://picsum.photos/seed/iphone2/200/200,https://picsum.photos/seed/iphone3/200/200',
      detailHtml: '<h1>iPhone 15 Pro Max</h1><p>详细介绍...</p>',
      detailMobileHtml: '<h1>iPhone 15 Pro Max</h1><p>移动端介绍...</p>',
    }
  }
})

const hideAll = () => { showStatus.value.fill(false) }

const prevStep = () => {
  if (active.value > 0 && active.value < showStatus.value.length) {
    active.value--
    hideAll()
    showStatus.value[active.value] = true
  }
}

const nextStep = () => {
  if (active.value < showStatus.value.length - 1) {
    active.value++
    hideAll()
    showStatus.value[active.value] = true
  }
}

const finishCommit = async (isEdit: boolean) => {
  await ElMessageBox.confirm('是否要提交该商品？', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  })
  ElMessage({ type: 'success', message: '提交成功', duration: 1000 })
  router.back()
}
</script>

<template>
  <el-card class="form-container" shadow="never">
    <el-steps :active="active" finish-status="success" align-center>
      <el-step title="填写商品信息"></el-step>
      <el-step title="填写商品促销"></el-step>
      <el-step title="填写商品属性"></el-step>
      <el-step title="选择商品关联"></el-step>
    </el-steps>
    <ProductInfoDetail v-show="showStatus[0]" :is-edit="isEdit" @next-step="nextStep" />
    <ProductSaleDetail v-show="showStatus[1]" :is-edit="isEdit" @next-step="nextStep" @prev-step="prevStep" />
    <ProductAttrDetail v-show="showStatus[2]" :is-edit="isEdit" @next-step="nextStep" @prev-step="prevStep" />
    <ProductRelationDetail v-show="showStatus[3]" :is-edit="isEdit" @prev-step="prevStep" @finish-commit="finishCommit" />
  </el-card>
</template>

<style scoped>
.form-container { width: 960px; margin: 0 auto; }
:deep(.form-inner-container) { width: 800px; margin: 0 auto; }
</style>
