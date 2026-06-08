<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'
import { couponTypes, couponPlatforms, useTypeOptions, memberLevelOptions } from '@/utils/constant'

const props = defineProps({
  isEdit: { type: Boolean, default: false },
  coupon: { type: Object, required: true },
})

const emit = defineEmits(['submit'])

const selectProduct = ref([])
const selectProductCate = ref([])

const productOptions = ref([
  { productId: 1, productName: 'iPhone 15 Pro Max', productSn: 'APP-2024-001' },
  { productId: 2, productName: '华为 Mate 60 Pro', productSn: 'HW-2024-002' },
  { productId: 3, productName: '小米14 Ultra', productSn: 'XM-2024-003' },
  { productId: 4, productName: 'MacBook Pro 14英寸', productSn: 'APP-2024-004' },
  { productId: 5, productName: 'AirPods Pro 2', productSn: 'APP-2024-005' },
  { productId: 6, productName: '华为 Watch GT 4', productSn: 'HW-2024-006' },
])

const productCateOptions = ref([
  { id: 1, name: '手机数码' },
  { id: 11, name: '手机', parentName: '手机数码' },
  { id: 12, name: '平板电脑', parentName: '手机数码' },
  { id: 2, name: '电脑办公' },
  { id: 21, name: '笔记本电脑', parentName: '电脑办公' },
  { id: 22, name: '台式机', parentName: '电脑办公' },
])

const couponForm = ref(props.coupon as any)

watch(selectProduct, (newVal) => {
  couponForm.value.productRelationList = newVal.map((id: number) => {
    const p = productOptions.value.find(item => item.productId === id)
    return { productId: id, productName: p?.productName, productSn: p?.productSn }
  })
})

watch(selectProductCate, (newVal) => {
  couponForm.value.productCategoryRelationList = newVal.map((id: number) => {
    const c = productCateOptions.value.find(item => item.id === id)
    return { productCategoryId: id, productCategoryName: c?.name, parentCategoryName: c?.parentName }
  })
})

onMounted(() => {
  if (props.isEdit) {
    selectProduct.value = couponForm.value.productRelationList?.map((item: any) => item.productId) || []
    selectProductCate.value = couponForm.value.productCategoryRelationList?.map((item: any) => item.productCategoryId) || []
  }
})

const handleSubmit = () => {
  emit('submit', couponForm.value)
}

const handleReset = () => {
  if (!props.isEdit) {
    Object.assign(couponForm.value, {
      type: 0, name: '', platform: 0, count: 0, amount: 0, perLimit: 1, minPoint: 0,
      startTime: '', endTime: '', useType: 0, note: '', publishCount: 0,
      code: '', memberLevel: 1, productRelationList: [], productCategoryRelationList: [],
    })
  }
}
</script>

<template>
  <el-card class="form-container" shadow="never">
    <el-form :model="couponForm" label-width="150px" style="width: 600px">
      <el-form-item label="优惠券类型：">
        <el-select v-model="couponForm.type" placeholder="请选择">
          <el-option v-for="item in couponTypes" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="优惠券名称：">
        <el-input v-model="couponForm.name" placeholder="请输入优惠券名称" />
      </el-form-item>
      <el-form-item label="适用平台：">
        <el-radio-group v-model="couponForm.platform">
          <el-radio v-for="item in couponPlatforms" :key="item.value" :label="item.value">{{ item.label }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="总发行量：">
        <el-input v-model="couponForm.publishCount" placeholder="只能输入正整数" />
      </el-form-item>
      <el-form-item label="面额：">
        <el-input v-model="couponForm.amount" placeholder="只能输入整数，单位是元" />
      </el-form-item>
      <el-form-item label="每人限领：">
        <el-input v-model="couponForm.perLimit" placeholder="只能输入整数" />
      </el-form-item>
      <el-form-item label="使用门槛：">
        满 <el-input v-model="couponForm.minPoint" style="width: 100px" placeholder="金额" /> 元可用
      </el-form-item>
      <el-form-item label="领取日期：">
        <el-date-picker v-model="couponForm.startTime" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        至
        <el-date-picker v-model="couponForm.endTime" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="可使用商品：">
        <el-radio-group v-model="couponForm.useType">
          <el-radio v-for="item in useTypeOptions" :key="item.value" :label="item.value">{{ item.label }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-show="couponForm.useType === 2">
        <el-transfer v-model="selectProduct" :titles="['待选择', '已选择']" :data="productOptions.map(p => ({ key: p.productId, label: p.productName }))" />
      </el-form-item>
      <el-form-item v-show="couponForm.useType === 1">
        <el-transfer v-model="selectProductCate" :titles="['待选择', '已选择']" :data="productCateOptions.map(c => ({ key: c.id, label: c.name }))" />
      </el-form-item>
      <el-form-item label="备注：">
        <el-input v-model="couponForm.note" type="textarea" :rows="3" placeholder="请输入备注" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
        <el-button v-if="!isEdit" @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.form-container { width: 800px; margin: 20px auto; }
</style>
