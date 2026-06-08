<script setup lang="ts">
import { ref, onMounted, watch, inject, type Ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['next-step'])

// 获取跨层数据
const compProductParam = inject('product-key') as Ref<any>

const selectProductCateValue = ref<number[]>([])
const productInfoForm = ref<FormInstance>()

const productCateOptions = ref([
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

const brandOptions = ref([
  { label: 'Apple', value: 1 },
  { label: '华为', value: 2 },
  { label: '小米', value: 3 },
  { label: 'Nike', value: 4 },
  { label: 'Adidas', value: 5 },
  { label: '索尼', value: 6 },
])

const rules = {
  name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 2, max: 140, message: '长度在 2 到 140 个字符', trigger: 'blur' }
  ],
  subTitle: [{ required: true, message: '请输入商品副标题', trigger: 'blur' }],
  productCategoryId: [{ required: true, message: '请选择商品分类', trigger: 'blur' }],
  brandId: [{ required: true, message: '请选择商品品牌', trigger: 'blur' }],
}

watch(selectProductCateValue, (newValue) => {
  if (newValue && newValue.length === 2) {
    compProductParam.value.productCategoryId = newValue[1]
    compProductParam.value.productCategoryName = getCateNameById(newValue[1])
  } else {
    compProductParam.value.productCategoryId = undefined
    compProductParam.value.productCategoryName = undefined
  }
})

onMounted(() => {
  if (props.isEdit) handleEditCreated()
})

const hasEditCreated = ref(false)

const handleEditCreated = () => {
  if (compProductParam.value.productCategoryId) {
    const cateId = compProductParam.value.productCategoryId
    for (const item of productCateOptions.value) {
      const child = item.children?.find(c => c.value === cateId)
      if (child) {
        selectProductCateValue.value = [item.value, cateId]
        break
      }
    }
  }
  hasEditCreated.value = true
}

const getCateNameById = (id: number) => {
  for (const item of productCateOptions.value) {
    const child = item.children?.find(c => c.value === id)
    if (child) return child.label
  }
  return undefined
}

const handleBrandChange = (val: number) => {
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
      <el-form-item label="商品分类：" prop="productCategoryId">
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
