<script setup lang="ts">
import { ref, onMounted, inject, type Ref, computed } from 'vue'

const props = defineProps({
  isEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['prev-step', 'finish-commit'])

const compProductParam = inject('product-key') as Ref<any>

const subjectList = ref([
  { label: '春季新品发布会', key: 1 },
  { label: '618年中大促', key: 2 },
  { label: '双11狂欢节', key: 3 },
  { label: '年终清仓', key: 4 },
  { label: '开学季数码专场', key: 5 },
  { label: '母亲节特惠', key: 6 },
  { label: '父亲节礼物精选', key: 7 },
  { label: '国庆黄金周', key: 8 },
])

const prefrenceAreaList = ref([
  { label: '首页推荐专区', key: 1 },
  { label: '新品首发专区', key: 2 },
  { label: '爆款热卖专区', key: 3 },
  { label: '限时秒杀专区', key: 4 },
  { label: '品牌特卖专区', key: 5 },
  { label: '会员专享专区', key: 6 },
])

const selectSubject = computed({
  get() {
    return compProductParam.value.subjectProductRelationList?.map((item: any) => item.subjectId) || []
  },
  set(newValue: number[]) {
    compProductParam.value.subjectProductRelationList = newValue?.map(item => ({ subjectId: item })) || []
  }
})

const selectPrefrenceArea = computed({
  get() {
    return compProductParam.value.prefrenceAreaProductRelationList?.map((item: any) => item.prefrenceAreaId) || []
  },
  set(newValue: number[]) {
    compProductParam.value.prefrenceAreaProductRelationList = newValue?.map(item => ({ prefrenceAreaId: item })) || []
  }
})

const filterMethod = (query: string, item: any) => item.label.indexOf(query) > -1

const handlePrev = () => { emit('prev-step') }
const handleFinishCommit = () => { emit('finish-commit', props.isEdit) }
</script>

<template>
  <div style="margin-top: 50px">
    <el-form :model="compProductParam" label-width="120px" class="form-inner-container">
      <el-form-item label="关联专题：">
        <el-transfer style="display: inline-block" filterable :filter-method="filterMethod" filter-placeholder="请输入专题名称"
          v-model="selectSubject" :titles="['待选择', '已选择']" :data="subjectList" />
      </el-form-item>
      <el-form-item label="关联优选：">
        <el-transfer style="display: inline-block" filterable :filter-method="filterMethod" filter-placeholder="请输入优选名称"
          v-model="selectPrefrenceArea" :titles="['待选择', '已选择']" :data="prefrenceAreaList" />
      </el-form-item>
      <el-form-item>
        <div style="width: 100%; text-align: center">
          <el-button @click="handlePrev">上一步，填写商品属性</el-button>
          <el-button type="primary" @click="handleFinishCommit">完成，提交商品</el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped></style>
