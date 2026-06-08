import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OmsOrder } from '@/types/order'

export const useOrderStore = defineStore('order', () => {
  const deliverOrderList = ref<OmsOrder[]>([])

  function setDeliverOrderList(list: OmsOrder[]) {
    deliverOrderList.value = list
  }

  return {
    deliverOrderList,
    setDeliverOrderList,
  }
})
