<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import CouponDetail from './components/CouponDetail.vue'

const router = useRouter()

const defaultCoupon = {
  type: 0, name: '', platform: 0, count: 0, amount: 0, perLimit: 1, minPoint: 0,
  startTime: '', endTime: '', useType: 0, note: '', publishCount: 0,
  code: '', memberLevel: 1, productRelationList: [], productCategoryRelationList: [],
}

const coupon = ref({ ...defaultCoupon })

const handleSubmit = (_coupon: any) => {
  ElMessage.success('添加成功!')
  router.back()
}
</script>

<template>
  <CouponDetail :is-edit="false" :coupon="coupon" @submit="handleSubmit" />
</template>
