<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import CouponDetail from './components/CouponDetail.vue'

const router = useRouter()
const route = useRoute()

const coupon = ref<any>({
  type: 0, name: '', platform: 0, count: 0, amount: 0, perLimit: 1, minPoint: 0,
  startTime: '', endTime: '', useType: 0, note: '', publishCount: 0,
  code: '', memberLevel: 1, productRelationList: [], productCategoryRelationList: [],
})

onMounted(() => {
  const id = Number(route.query.id)
  if (id) {
    coupon.value = {
      id, type: 2, name: '618购物返券', platform: 1, count: 500, amount: 30, perLimit: 2,
      minPoint: 300, startTime: '2024-06-10', endTime: '2024-06-20', useType: 0,
      note: '618活动专用', publishCount: 500, code: '', memberLevel: 1,
      productRelationList: [], productCategoryRelationList: [],
    }
  }
})

const handleSubmit = (_coupon: any) => {
  ElMessage.success('修改成功!')
  router.back()
}
</script>

<template>
  <CouponDetail :is-edit="true" :coupon="coupon" @submit="handleSubmit" />
</template>
