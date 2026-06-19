<script setup lang="ts">
import { ref, onMounted, watch, inject, type Ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { getBrandAllAPI } from '@/apis/brand'
import { getProductCategoryListWithChildrenAPI } from '@/apis/productCate'
import type { PmsProductCategory } from '@/types/productCate'

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['next-step'])

// 获取跨层数据
const compProductParam = inject('product-key') as Ref<any>

const selectProductCateValue = ref<string[]>([])
const productInfoForm = ref<FormInstance>()

interface CascaderOption {
  label: string
  value: string
  children?: CascaderOption[]
}

const productCateOptions = ref<CascaderOption[]>([])
const brandOptions = ref<Array<{ label: string; value: string }>>([])

const rules = {
  name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 2, max: 140, message: '长度在 2 到 140 个字符', trigger: 'blur' }
  ],
  subTitle: [{ required: true, message: '请输入商品副标题', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择商品分类', trigger: 'blur' }],
  brandId: [{ required: true, message: '请选择商品品牌', trigger: 'blur' }],
}

watch(selectProductCateValue, (newValue) => {
  if (newValue && newValue.length > 0) {
    const categoryId = newValue[newValue.length - 1]
    compProductParam.value.categoryId = categoryId
    compProductParam.value.productCategoryName = getCateNameById(categoryId)
  } else {
    compProductParam.value.categoryId = undefined
    compProductParam.value.productCategoryName = undefined
  }
})

watch(
  () => compProductParam.value.categoryId,
  (categoryId) => {
    if (props.isEdit && categoryId) handleEditCreated()
  },
)

onMounted(async () => {
  await loadOptions()
  if (props.isEdit) handleEditCreated()
})

const hasEditCreated = ref(false)

const handleEditCreated = () => {
  if (compProductParam.value.categoryId) {
    selectProductCateValue.value = findCategoryPath(
      productCateOptions.value,
      compProductParam.value.categoryId,
    )
  }
  hasEditCreated.value = true
}

const getCateNameById = (id: string): string | undefined => {
  for (const item of productCateOptions.value) {
    if (item.value === id) return item.label
    const childName = item.children ? getCateNameFromTree(item.children, id) : undefined
    if (childName) return childName
  }
  return undefined
}

function getCateNameFromTree(options: CascaderOption[], id: string): string | undefined {
  for (const option of options) {
    if (option.value === id) return option.label
    const childName = option.children ? getCateNameFromTree(option.children, id) : undefined
    if (childName) return childName
  }
  return undefined
}

function findCategoryPath(options: CascaderOption[], id: string): string[] {
  for (const option of options) {
    if (option.value === id) return [option.value]
    if (option.children) {
      const childPath = findCategoryPath(option.children, id)
      if (childPath.length > 0) return [option.value, ...childPath]
    }
  }
  return []
}

function mapCategoryTree(categories: PmsProductCategory[]): CascaderOption[] {
  return categories.map((category) => ({
    label: category.name,
    value: category.id || '',
    children: category.children?.length ? mapCategoryTree(category.children) : undefined,
  }))
}

async function loadOptions(): Promise<void> {
  try {
    const [brandResponse, categoryResponse] = await Promise.all([
      getBrandAllAPI(),
      getProductCategoryListWithChildrenAPI(),
    ])
    brandOptions.value = brandResponse.data.map((brand) => ({
      label: brand.name,
      value: brand.id || '',
    }))
    productCateOptions.value = mapCategoryTree(categoryResponse.data)
  } catch {
    ElMessage.error('加载品牌和商品分类失败')
  }
}

const handleBrandChange = (val: string) => {
  const findBrand = brandOptions.value.find(item => item.value === val)
  compProductParam.value.brandName = findBrand?.label
}

const handleNext = async () => {
  if (!productInfoForm.value) return
  try {
    const valid = await productInfoForm.value.validate()
    if (valid) emit('next-step')
  } catch {
    ElMessage({ message: '验证失败', type: 'error', duration: 1000 })
  }
}
</script>

<template>
  <div style="margin-top: 50px">
    <el-form :model="compProductParam" :rules="rules" ref="productInfoForm" label-width="120px" class="form-inner-container">
      <el-form-item label="商品分类：" prop="categoryId">
        <el-cascader v-model="selectProductCateValue" :options="productCateOptions" placeholder="请选择" />
      </el-form-item>
      <el-form-item label="商品名称：" prop="name">
        <el-input v-model="compProductParam.name" placeholder="请输入商品名称" />
      </el-form-item>
      <el-form-item label="副标题：" prop="subTitle">
        <el-input v-model="compProductParam.subTitle" placeholder="请输入副标题" />
      </el-form-item>
      <el-form-item label="商品品牌：" prop="brandId">
        <el-select v-model="compProductParam.brandId" @change="handleBrandChange" placeholder="请选择品牌">
          <el-option v-for="item in brandOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品介绍：">
        <el-input :autosize="{ minRows: 3 }" v-model="compProductParam.description" type="textarea" placeholder="请输入商品介绍" />
      </el-form-item>
      <el-form-item label="商品货号：">
        <el-input v-model="compProductParam.productSn" placeholder="请输入商品货号" />
      </el-form-item>
      <el-form-item label="商品售价：">
        <el-input v-model="compProductParam.price" placeholder="请输入售价" />
      </el-form-item>
      <el-form-item label="市场价：">
        <el-input v-model="compProductParam.originalPrice" placeholder="请输入市场价" />
      </el-form-item>
      <el-form-item label="商品库存：">
        <el-input v-model="compProductParam.stock" placeholder="请输入库存" />
      </el-form-item>
      <el-form-item label="计量单位：">
        <el-input v-model="compProductParam.unit" placeholder="件/个/套" />
      </el-form-item>
      <el-form-item label="商品重量：">
        <el-input v-model="compProductParam.weight" style="width: 300px" placeholder="请输入重量" />
        <span style="margin-left: 20px">克</span>
      </el-form-item>
      <el-form-item label="排序：">
        <el-input v-model="compProductParam.sort" placeholder="请输入排序" />
      </el-form-item>
      <el-form-item>
        <div style="width: 100%; text-align: center;">
          <el-button type="primary" @click="handleNext">下一步，填写商品促销</el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped></style>
