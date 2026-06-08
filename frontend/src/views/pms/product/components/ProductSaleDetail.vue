<script setup lang="ts">
import { ref, computed, inject, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['prev-step', 'next-step'])

const compProductParam = inject('product-key') as Ref<any>

const memberPriceList = ref([
  { memberLevelId: 1, memberLevelName: '普通会员', memberPrice: 0 },
  { memberLevelId: 2, memberLevelName: '黄金会员', memberPrice: 0 },
  { memberLevelId: 3, memberLevelName: '白金会员', memberPrice: 0 },
])

const selectServiceList = computed({
  get() {
    if (!compProductParam.value.serviceIds) return []
    return compProductParam.value.serviceIds.split(',').map((item: string) => Number(item))
  },
  set(newValue: number[]) {
    if (newValue && newValue.length > 0) {
      compProductParam.value.serviceIds = newValue.join(',')
    } else {
      compProductParam.value.serviceIds = ''
    }
  }
})

const handleRemoveProductLadder = (index: number) => {
  const list = compProductParam.value.productLadderList
  if (list.length === 1) {
    list.splice(0, 1, { count: 0, discount: 0, price: 0 })
  } else {
    list.splice(index, 1)
  }
}

const handleAddProductLadder = () => {
  const list = compProductParam.value.productLadderList
  if (list.length < 3) {
    list.push({ count: 0, discount: 0, price: 0 })
  } else {
    ElMessage({ message: '最多只能添加三条', type: 'warning' })
  }
}

const handleRemoveFullReduction = (index: number) => {
  const list = compProductParam.value.productFullReductionList
  if (list.length === 1) {
    list.splice(0, 1, { fullPrice: 0, reducePrice: 0 })
  } else {
    list.splice(index, 1)
  }
}

const handleAddFullReduction = () => {
  const list = compProductParam.value.productFullReductionList
  if (list.length < 3) {
    list.push({ fullPrice: 0, reducePrice: 0 })
  } else {
    ElMessage({ message: '最多只能添加三条', type: 'warning' })
  }
}

const handlePrev = () => { emit('prev-step') }
const handleNext = () => { emit('next-step') }

const isDisabledDate = (time: Date) => time.getTime() < Date.now()
</script>

<template>
  <div style="margin-top: 50px">
    <el-form :model="compProductParam" label-width="120px" class="form-inner-container">
      <el-form-item label="赠送积分：">
        <el-input v-model="compProductParam.giftPoint" placeholder="请输入赠送积分" />
      </el-form-item>
      <el-form-item label="赠送成长值：">
        <el-input v-model="compProductParam.giftGrowth" placeholder="请输入赠送成长值" />
      </el-form-item>
      <el-form-item label="积分购买限制：">
        <el-input v-model="compProductParam.usePointLimit" placeholder="请输入积分购买限制" />
      </el-form-item>
      <el-form-item label="预告商品：">
        <el-switch v-model="compProductParam.previewStatus" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="商品上架：">
        <el-switch v-model="compProductParam.publishStatus" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="商品推荐：">
        <span style="margin-right: 10px">新品</span>
        <el-switch v-model="compProductParam.newStatus" :active-value="1" :inactive-value="0" />
        <span style="margin-left: 10px; margin-right: 10px">推荐</span>
        <el-switch v-model="compProductParam.recommandStatus" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="服务保证：">
        <el-checkbox-group v-model="selectServiceList">
          <el-checkbox :label="1">无忧退货</el-checkbox>
          <el-checkbox :label="2">快速退款</el-checkbox>
          <el-checkbox :label="3">免费包邮</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      <el-form-item label="详细页标题：">
        <el-input v-model="compProductParam.detailTitle" placeholder="请输入详细页标题" />
      </el-form-item>
      <el-form-item label="详细页描述：">
        <el-input v-model="compProductParam.detailDesc" placeholder="请输入详细页描述" />
      </el-form-item>
      <el-form-item label="商品关键字：">
        <el-input v-model="compProductParam.keywords" placeholder="请输入关键字" />
      </el-form-item>
      <el-form-item label="商品备注：">
        <el-input v-model="compProductParam.note" type="textarea" :autosize="{ minRows: 2 }" placeholder="请输入备注" />
      </el-form-item>
      <el-form-item label="选择优惠方式：">
        <el-radio-group v-model="compProductParam.promotionType">
          <el-radio-button :label="0">无优惠</el-radio-button>
          <el-radio-button :label="1">特惠促销</el-radio-button>
          <el-radio-button :label="2">会员价格</el-radio-button>
          <el-radio-button :label="3">阶梯价格</el-radio-button>
          <el-radio-button :label="4">满减价格</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-show="compProductParam.promotionType === 1">
        <div>
          <div>开始时间：<el-date-picker v-model="compProductParam.promotionStartTime" type="datetime" :disabled-date="isDisabledDate" placeholder="选择开始时间" /></div>
          <div class="littleMargin">结束时间：<el-date-picker v-model="compProductParam.promotionEndTime" type="datetime" :disabled-date="isDisabledDate" placeholder="选择结束时间" /></div>
          <div class="littleMargin">促销价格：<el-input style="width: 220px" v-model="compProductParam.promotionPrice" placeholder="输入促销价格" /></div>
        </div>
      </el-form-item>
      <el-form-item v-show="compProductParam.promotionType === 2">
        <div v-for="(item, index) in memberPriceList" :class="{ littleMargin: index !== 0 }" :key="item.memberLevelId">
          {{ item.memberLevelName }}：<el-input v-model="item.memberPrice" style="width: 200px" />
        </div>
      </el-form-item>
      <el-form-item v-show="compProductParam.promotionType === 3">
        <el-table :data="compProductParam.productLadderList" style="width: 80%" border>
          <el-table-column label="数量" align="center" width="120">
            <template #default="scope"><el-input v-model="scope.row.count" /></template>
          </el-table-column>
          <el-table-column label="折扣" align="center" width="120">
            <template #default="scope"><el-input v-model="scope.row.discount" /></template>
          </el-table-column>
          <el-table-column align="center" label="操作">
            <template #default="scope">
              <el-button link type="primary" @click="handleRemoveProductLadder(scope.$index)">删除</el-button>
              <el-button link type="primary" @click="handleAddProductLadder()">添加</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form-item>
      <el-form-item v-show="compProductParam.promotionType === 4">
        <el-table :data="compProductParam.productFullReductionList" style="width: 80%" border>
          <el-table-column label="满" align="center" width="120">
            <template #default="scope"><el-input v-model="scope.row.fullPrice" /></template>
          </el-table-column>
          <el-table-column label="立减" align="center" width="120">
            <template #default="scope"><el-input v-model="scope.row.reducePrice" /></template>
          </el-table-column>
          <el-table-column align="center" label="操作">
            <template #default="scope">
              <el-button link type="primary" @click="handleRemoveFullReduction(scope.$index)">删除</el-button>
              <el-button link type="primary" @click="handleAddFullReduction()">添加</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form-item>
      <el-form-item>
        <div style="width: 100%; text-align: center">
          <el-button @click="handlePrev">上一步，填写商品信息</el-button>
          <el-button type="primary" @click="handleNext">下一步，填写商品属性</el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.littleMargin { margin-top: 10px; }
</style>
