<script setup lang="ts">
/**
 * 省市区三级级联选择器 — CDN 动态加载 china-area-data
 * 用法: <RegionCascader v-model:province="..." v-model:city="..." v-model:region="..." />
 */
import { ref, computed, watch, onMounted } from 'vue'
import { fetchRegionTree, type RegionItem } from '@/data/region'

const props = defineProps<{
  province: string
  city: string
  region: string
}>()

const emit = defineEmits<{
  'update:province': [value: string]
  'update:city': [value: string]
  'update:region': [value: string]
}>()

// ── 异步数据 ──
const regions = ref<RegionItem[]>([])
const loading = ref(true)
const loadError = ref(false)

onMounted(async () => {
  try {
    regions.value = await fetchRegionTree()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})

// ── 内部选中值 ──
const selectedProvince = ref(props.province)
const selectedCity = ref(props.city)
const selectedRegion = ref(props.region)

const cities = computed<RegionItem[]>(() => {
  const p = regions.value.find((r) => r.value === selectedProvince.value)
  return p?.children || []
})

const districts = computed<RegionItem[]>(() => {
  const c = cities.value.find((c) => c.value === selectedCity.value)
  return c?.children || []
})

// ── 选择联动 ──
function onProvinceChange() {
  selectedRegion.value = ''
  emit('update:province', selectedProvince.value)
  // 直辖市只有1个城市 → 自动选中
  const opts = cities.value
  if (opts.length === 1) {
    selectedCity.value = opts[0].value
    emit('update:city', opts[0].value)
  } else {
    selectedCity.value = ''
    emit('update:city', '')
  }
  emit('update:region', '')
}

function onCityChange() {
  selectedRegion.value = ''
  emit('update:city', selectedCity.value)
  emit('update:region', '')
}

function onRegionChange() {
  emit('update:region', selectedRegion.value)
}

// ── 外部变更同步（编辑已有地址时回显） ──
watch(() => props.province, (v) => { selectedProvince.value = v })
watch(() => props.city, (v) => { selectedCity.value = v })
watch(() => props.region, (v) => { selectedRegion.value = v })
</script>

<template>
  <!-- 加载中 -->
  <div v-if="loading" class="grid grid-cols-3 gap-3">
    <div class="h-10 bg-gray-100 rounded-lg animate-pulse" />
    <div class="h-10 bg-gray-100 rounded-lg animate-pulse" />
    <div class="h-10 bg-gray-100 rounded-lg animate-pulse" />
  </div>

  <!-- 加载失败 -->
  <div v-else-if="loadError" class="text-sm text-red-500 py-2">
    地区数据加载失败，请刷新页面重试
  </div>

  <!-- 正常选择器 -->
  <div v-else class="grid grid-cols-3 gap-3">
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1.5">省/直辖市 <span class="text-red-400">*</span></label>
      <select
        v-model="selectedProvince"
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent appearance-none"
        @change="onProvinceChange"
      >
        <option value="" disabled>请选择省</option>
        <option v-for="p in regions" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1.5">城市 <span class="text-red-400">*</span></label>
      <select
        v-model="selectedCity"
        :disabled="!selectedProvince"
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent appearance-none disabled:bg-gray-50 disabled:text-gray-400"
        @change="onCityChange"
      >
        <option value="" disabled>请选择城市</option>
        <option v-for="c in cities" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1.5">区/县 <span class="text-red-400">*</span></label>
      <select
        v-model="selectedRegion"
        :disabled="!selectedCity"
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent appearance-none disabled:bg-gray-50 disabled:text-gray-400"
        @change="onRegionChange"
      >
        <option value="" disabled>请选择区/县</option>
        <option v-for="r in districts" :key="r.value" :value="r.value">{{ r.label }}</option>
      </select>
    </div>
  </div>
</template>
