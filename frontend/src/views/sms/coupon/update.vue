<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCouponByIdAPI, createCouponAPI, updateCouponByIdAPI } from '@/apis/coupon'
import { couponTypes, couponPlatforms, useTypeOptions } from '@/utils/constant'

const router = useRouter()
const route = useRoute()

const mode = computed(() => (route.query.mode as string) || 'edit')
const isCreate = computed(() => mode.value === 'add')
const isDetail = computed(() => mode.value === 'detail')

// ── form data ──
const coupon = ref<any>({
  type: 0, name: '', platform: 0, count: 0, amount: 0, perLimit: 1, minPoint: 0,
  startTime: '', endTime: '', useType: 0, note: '', publishCount: 0,
  code: '', memberLevel: 1, productRelationList: [], productCategoryRelationList: [],
})

const selectProduct = ref<number[]>([])
const selectProductCate = ref<number[]>([])

const productOptions = [
  { productId: 1, productName: 'iPhone 15 Pro Max', productSn: 'APP-2024-001' },
  { productId: 2, productName: '华为 Mate 60 Pro', productSn: 'HW-2024-002' },
  { productId: 3, productName: '小米14 Ultra', productSn: 'XM-2024-003' },
  { productId: 4, productName: 'MacBook Pro 14英寸', productSn: 'APP-2024-004' },
  { productId: 5, productName: 'AirPods Pro 2', productSn: 'APP-2024-005' },
  { productId: 6, productName: '华为 Watch GT 4', productSn: 'HW-2024-006' },
]

const productCateOptions = [
  { id: 1, name: '手机数码', parentName: null },
  { id: 11, name: '手机', parentName: '手机数码' },
  { id: 12, name: '平板电脑', parentName: '手机数码' },
  { id: 2, name: '电脑办公', parentName: null },
  { id: 21, name: '笔记本电脑', parentName: '电脑办公' },
  { id: 22, name: '台式机', parentName: '电脑办公' },
]

// ── load existing data ──
onMounted(async () => {
  if (isCreate.value) return

  const id = route.query.id as string
  if (!id) {
    ElMessage.error('优惠券ID不能为空')
    router.replace('/sms/coupon')
    return
  }
  try {
    coupon.value = await getCouponByIdAPI(id)
    selectProduct.value = coupon.value.productRelationList?.map((item: any) => item.productId) || []
    selectProductCate.value = coupon.value.productCategoryRelationList?.map((item: any) => item.productCategoryId) || []
  } catch {
    ElMessage.error('加载优惠券详情失败')
  }
})

// ── submit ──
const submitting = ref(false)
const handleSubmit = async () => {
  submitting.value = true
  try {
    if (isCreate.value) {
      await createCouponAPI(coupon.value)
      ElMessage.success('添加成功!')
    } else {
      await updateCouponByIdAPI(route.query.id as string, coupon.value)
      ElMessage.success('修改成功!')
    }
    router.back()
  } catch {
    ElMessage.error(isCreate.value ? '添加失败' : '修改失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-card class="form-container" shadow="never">
    <el-form :model="coupon" label-width="150px" style="width: 600px" :disabled="isDetail">
      <el-form-item label="优惠券类型：">
        <el-select v-model="coupon.type" placeholder="请选择">
          <el-option v-for="t in couponTypes" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="优惠券名称：">
        <el-input v-model="coupon.name" placeholder="请输入优惠券名称" />
      </el-form-item>
      <el-form-item label="适用平台：">
        <el-radio-group v-model="coupon.platform">
          <el-radio v-for="p in couponPlatforms" :key="p.value" :label="p.value">{{ p.label }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="总发行量：">
        <el-input v-model="coupon.publishCount" placeholder="只能输入正整数" />
      </el-form-item>
      <el-form-item label="面额：">
        <el-input v-model="coupon.amount" placeholder="只能输入整数，单位是元" />
      </el-form-item>
      <el-form-item label="每人限领：">
        <el-input v-model="coupon.perLimit" placeholder="只能输入整数" />
      </el-form-item>
      <el-form-item label="使用门槛：">
        满 <el-input v-model="coupon.minPoint" style="width: 100px" placeholder="金额" /> 元可用
      </el-form-item>
      <el-form-item label="领取日期：">
        <el-date-picker v-model="coupon.startTime" type="date" value-format="YYYY-MM-DD" />
        至
        <el-date-picker v-model="coupon.endTime" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="可使用商品：">
        <el-radio-group v-model="coupon.useType">
          <el-radio v-for="u in useTypeOptions" :key="u.value" :label="u.value">{{ u.label }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-show="coupon.useType === 2">
        <el-transfer v-model="selectProduct" :titles="['待选择', '已选择']" :data="productOptions.map(p => ({ key: p.productId, label: p.productName }))" />
      </el-form-item>
      <el-form-item v-show="coupon.useType === 1">
        <el-transfer v-model="selectProductCate" :titles="['待选择', '已选择']" :data="productCateOptions.map(c => ({ key: c.id, label: c.name }))" />
      </el-form-item>
      <el-form-item label="备注：">
        <el-input v-model="coupon.note" type="textarea" :rows="3" placeholder="请输入备注" />
      </el-form-item>
      <el-form-item v-if="!isDetail">
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
        <el-button v-if="isCreate" @click="coupon = { type: 0, name: '', platform: 0, count: 0, amount: 0, perLimit: 1, minPoint: 0, startTime: '', endTime: '', useType: 0, note: '', publishCount: 0, code: '', memberLevel: 1, productRelationList: [], productCategoryRelationList: [] }">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.form-container { width: 800px; margin: 20px auto; }
</style>
