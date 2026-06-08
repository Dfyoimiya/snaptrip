<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

const defaultLogisticsList = [
  { name: '订单已提交，等待付款', time: '2024-05-28 12:00:00' },
  { name: '订单付款成功', time: '2024-05-28 12:05:00' },
  { name: '商家已确认，正在配货', time: '2024-05-28 14:30:00' },
  { name: '商品已打包，等待揽收', time: '2024-05-28 16:00:00' },
  { name: '顺丰速运已揽件', time: '2024-05-28 18:00:00' },
  { name: '快件到达深圳转运中心', time: '2024-05-29 02:00:00' },
  { name: '到达目的地网点，快件将很快进行派送', time: '2024-05-29 08:00:00' },
  { name: '订单已签收，期待再次为您服务', time: '2024-05-29 14:00:00' },
]

const logisticsList = ref([...defaultLogisticsList])

const visible = computed({
  get() { return props.modelValue },
  set(val) { emit('update:modelValue', val) }
})
</script>

<template>
  <el-dialog title="订单跟踪" v-model="visible" width="40%">
    <el-steps direction="vertical" :active="7" finish-status="success" space="50px">
      <el-step v-for="item in logisticsList" :key="item.name" :title="item.name" :description="item.time" />
    </el-steps>
  </el-dialog>
</template>
