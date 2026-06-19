<script setup lang="ts">
import { ref, onMounted, watch, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createProductAPI,
  createProductSkuAPI,
  deleteProductSkuAPI,
  getProductAPI,
  updateProductAPI,
  updateProductAttributesAPI,
  updateProductSkuAPI,
} from '@/apis/product'
import type { PmsProductParam, ProductAttrValue, SkuStock } from '@/types/product'
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
  freightTemplateId: '',
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
  defaultPic: '',
  memberPriceList: [] as unknown[],
  productFullReductionList: [{ fullPrice: 0, reducePrice: 0 }],
  productLadderList: [{ count: 0, discount: 0, price: 0 }],
  previewStatus: 0,
  price: 0,
  productAttributeValueList: [] as ProductAttrValue[],
  skuStockList: [] as SkuStock[],
  subjectProductRelationList: [] as unknown[],
  prefrenceAreaProductRelationList: [] as unknown[],
  productCategoryName: '',
  productSn: '',
  promotionEndTime: '',
  promotionPerLimit: 0,
  promotionStartTime: '',
  promotionType: 0,
  publishStatus: 0,
  recommendStatus: 0,
  saleCount: 0,
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
const pageLoading = ref(false)
const submitting = ref(false)
const editingProductId = ref<string>('')
const originalSkuIds = ref<string[]>([])

// 跨层传递数据
provide('product-key', productParam)

onMounted(() => {
  if (!props.isEdit) return
  const id = route.query.id as string
  if (!id) {
    ElMessage.error('商品ID不能为空，请从商品列表进入')
    router.replace('/pms/product')
    return
  }
  editingProductId.value = id
  loadProduct(id)
})

watch(() => route.query.id, (newId) => {
  if (!props.isEdit || !newId) return
  editingProductId.value = newId as string
  loadProduct(newId as string)
})

async function loadProduct(productId: string) {
  pageLoading.value = true
  try {
    const data = await getProductAPI(productId)
    const detail = data.data
    const skuStockList: SkuStock[] = (detail.skus || []).map((sku) => ({
      id: sku.id,
      productId: sku.productId,
      skuCode: sku.skuCode,
      price: sku.price,
      promotionPrice: sku.promotionPrice,
      stock: sku.stock,
      lowStock: sku.lowStock,
      defaultPic: sku.pic,
      spec: sku.spec,
      spData: sku.spec,
    }))
    const productAttributeValueList: ProductAttrValue[] = (detail.attributeValues || []).map(
      (item: { attributeId: string; value: string }) => ({
        productAttributeId: item.attributeId,
        value: item.value,
      }),
    )
    originalSkuIds.value = skuStockList
      .map((sku) => sku.id)
      .filter((id): id is string => Boolean(id))
    productParam.value = {
      ...defaultProductParam,
      ...detail,
      productCategoryName: detail.categoryName || '',
      skuStockList,
      productAttributeValueList,
    }
  } catch {
    ElMessage.error('加载商品详情失败')
  } finally {
    pageLoading.value = false
  }
}

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
  try {
    await ElMessageBox.confirm('是否要提交该商品？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    })
    submitting.value = true
    if (isEdit) {
      if (!editingProductId.value) {
        ElMessage.error('商品ID缺失，请从商品列表重新进入')
        router.replace('/pms/product')
        return
      }
      await updateProductAPI(editingProductId.value, productParam.value as any)
      await syncProductRelations(editingProductId.value)
    } else {
      await createProductAPI(productParam.value as any)
    }
    ElMessage({
      type: 'success',
      message: isEdit ? '商品已更新，列表和数据库已同步' : '商品已添加，列表和数据库已同步',
      duration: 1500,
    })
    await router.replace('/pms/product')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

async function syncProductRelations(productId: string): Promise<void> {
  const currentSkus = (productParam.value.skuStockList || []) as SkuStock[]
  const currentSkuIds = new Set(
    currentSkus.map((sku) => sku.id).filter((id): id is string => Boolean(id)),
  )

  for (const sku of currentSkus) {
    if (sku.id) {
      await updateProductSkuAPI(productId, sku.id, sku)
    } else {
      await createProductSkuAPI(productId, sku)
    }
  }

  if (currentSkus.length > 0) {
    for (const skuId of originalSkuIds.value) {
      if (!currentSkuIds.has(skuId)) {
        await deleteProductSkuAPI(productId, skuId)
      }
    }
  }

  const attributeValues = Object.fromEntries(
    ((productParam.value.productAttributeValueList || []) as ProductAttrValue[])
      .filter((item) => item.productAttributeId)
      .map((item) => [item.productAttributeId, item.value]),
  )
  await updateProductAttributesAPI(productId, attributeValues)
}
</script>

<template>
  <el-card v-loading="pageLoading || submitting" class="form-container" shadow="never">
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
