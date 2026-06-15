<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCouponByIdAPI, createCouponAPI, updateCouponByIdAPI } from '@/apis/coupon'
import { couponTypes, couponPlatforms, useTypeOptions } from '@/utils/constant'
import { getProductListAPI } from '@/apis/product'
import { getProductCategoryListWithChildrenAPI } from '@/apis/productCate'

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

const selectProduct = ref<string[]>([])
const selectProductCate = ref<string[]>([])

// 从 API 获取的真实商品/分类数据
const productOptions = ref<{ productId: string; productName: string; productSn: string }[]>([])
const productCateOptions = ref<{ id: string; name: string; parentName: string | null }[]>([])

// ── load existing data ──
onMounted(async () => {
  // 并行加载产品和分类列表
  try {
    const [prodRes, cateRes] = await Promise.all([
      getProductListAPI({ keyword: '', page: 1, page_size: 100 }),
      getProductCategoryListWithChildrenAPI(),
    ])
    productOptions.value = (prodRes.data?.items || []).map((p: any) => ({
      productId: p.id || '',
      productName: p.name || '',
      productSn: p.productSn || '',
    }))
    productCateOptions.value = (cateRes.data || []).map((c: any) => ({
      id: c.id || '',
      name: c.name || '',
      parentName: c.parentName || null,
    }))
  } catch {
    // 静默失败，选项保持为空
  }

  if (isCreate.value) return

  const id = route.query.id as string
  if (!id) {
    ElMessage.error('优惠券ID不能为空')
    router.replace('/sms/coupon')
    return
  }
  try {
    coupon.value = await getCouponByIdAPI(id)
    selectProduct.value = coupon.value.productRelationList?.map((item: any) => String(item.productId)) || []
    selectProductCate.value = coupon.value.productCategoryRelationList?.map((item: any) => String(item.productCategoryId)) || []
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
