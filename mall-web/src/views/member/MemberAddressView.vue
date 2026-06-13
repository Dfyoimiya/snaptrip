<script setup lang="ts">
/**
 * ============================================
 * 收货地址页 (MemberAddressView)
 * PC 端：卡片式列表 + Dialog 弹窗 + 省市区联动级联选择器
 * ============================================
 */
import { ref } from 'vue'
import type { MemberReceiveAddress } from '@/types/address'
import { provinceData } from '@/data/region'

// ===== 级联选择器相关 =====
const provinceList = provinceData

/** 根据省份获取城市列表 */
const getCityList = (province: string) => {
  const p = provinceList.find(p => p.value === province)
  return p?.children || []
}

/** 根据城市获取区县列表 */
const getRegionList = (province: string, city: string) => {
  const p = provinceList.find(p => p.value === province)
  const c = p?.children?.find(c => c.value === city)
  return c?.children || []
}

/** 级联选择器选中的路径 */
const cascadePath = ref<string[]>([])
const selectedProvince = ref('')
const selectedCity = ref('')
const selectedRegion = ref('')

// ===== 地址数据 =====
const addresses = ref<MemberReceiveAddress[]>([
  { id: 1, memberId: 1, name: '张三', phoneNumber: '13800138000', defaultStatus: 1, province: '上海市', city: '上海市', region: '浦东新区', detailAddress: '陆家嘴环路1000号恒生银行大厦28楼' },
  { id: 2, memberId: 1, name: '李四', phoneNumber: '13900139000', defaultStatus: 0, province: '北京市', city: '北京市', region: '朝阳区', detailAddress: '建国路88号SOHO现代城B座1502室' },
  { id: 3, memberId: 1, name: '王五', phoneNumber: '13700137000', defaultStatus: 0, province: '广东省', city: '深圳市', region: '南山区', detailAddress: '科技园科苑路15号科兴科学园B栋3单元1201' },
])

// ===== Dialog 相关 =====
const showDialog = ref(false)
const dialogTitle = ref('新增地址')
const editingAddress = ref<Partial<MemberReceiveAddress>>({
  name: '', phoneNumber: '', detailAddress: '', defaultStatus: 0,
})
const formErrors = ref<Record<string, string>>({})

// ===== 操作 =====
const resetForm = () => {
  editingAddress.value = { name: '', phoneNumber: '', detailAddress: '', defaultStatus: 0 }
  selectedProvince.value = ''
  selectedCity.value = ''
  selectedRegion.value = ''
  formErrors.value = {}
}

const openAddDialog = () => {
  resetForm()
  dialogTitle.value = '新增收货地址'
  showDialog.value = true
}

const openEditDialog = (addr: MemberReceiveAddress) => {
  editingAddress.value = { ...addr }
  selectedProvince.value = addr.province || ''
  selectedCity.value = addr.city || ''
  selectedRegion.value = addr.region || ''
  dialogTitle.value = '编辑收货地址'
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

/** 省份变化时重置城市和区县 */
const onProvinceChange = () => {
  selectedCity.value = ''
  selectedRegion.value = ''
}

/** 城市变化时重置区县 */
const onCityChange = () => {
  selectedRegion.value = ''
}

const validateForm = () => {
  const errors: Record<string, string> = {}
  if (!editingAddress.value.name?.trim()) errors.name = '请输入收货人姓名'
  if (!editingAddress.value.phoneNumber) errors.phoneNumber = '请输入手机号'
  else if (!/^1[3-9]\d{9}$/.test(editingAddress.value.phoneNumber)) errors.phoneNumber = '手机号格式不正确'
  if (!selectedProvince.value || !selectedCity.value || !selectedRegion.value) errors.region = '请选择完整的省市区'
  if (!editingAddress.value.detailAddress?.trim()) errors.detailAddress = '请输入详细地址'
  formErrors.value = errors
  return Object.keys(errors).length === 0
}

const handleSave = () => {
  if (!validateForm()) return
  const data = {
    ...editingAddress.value,
    province: selectedProvince.value,
    city: selectedCity.value,
    region: selectedRegion.value,
  }
  if (editingAddress.value.id) {
    const idx = addresses.value.findIndex(a => a.id === editingAddress.value.id)
    if (idx >= 0) addresses.value[idx] = { ...addresses.value[idx], ...data } as MemberReceiveAddress
  } else {
    addresses.value.push({ ...data, id: Date.now(), memberId: 1 } as MemberReceiveAddress)
  }
  showDialog.value = false
}

const handleDelete = (id?: number) => {
  if (confirm('确定删除该地址吗？')) {
    addresses.value = addresses.value.filter(a => a.id !== id)
  }
}

const handleSetDefault = (id?: number) => {
  addresses.value.forEach(a => { a.defaultStatus = a.id === id ? 1 : 0 })
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[500px]">
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
      <h2 class="text-lg font-bold text-gray-900">收货地址</h2>
      <span class="text-sm text-gray-400 mr-4">已保存 {{ addresses.length }} 个地址（最多20个）</span>
    </div>

    <!-- 地址卡片网格 -->
    <div class="p-5 grid grid-cols-2 gap-4">
      <!-- 新增地址卡片 -->
      <button
        class="h-40 border-2 border-dashed border-gray-200 rounded-lg flex flex-col items-center justify-center gap-2 text-gray-400 hover:border-red-300 hover:text-red-500 transition-colors"
        @click="openAddDialog"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        <span class="text-sm font-medium">新增收货地址</span>
      </button>

      <!-- 地址卡片 -->
      <div
        v-for="addr in addresses"
        :key="addr.id"
        :class="[
          'relative p-4 rounded-lg border transition-all',
          addr.defaultStatus === 1
            ? 'border-red-300 bg-red-50/40 shadow-sm'
            : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm',
        ]"
      >
        <!-- 默认标签 -->
        <span
          v-if="addr.defaultStatus === 1"
          class="absolute top-3 right-3 text-xs bg-red-600 text-white px-2 py-0.5 rounded font-medium"
        >默认</span>

        <!-- 地址内容 -->
        <div class="pr-16">
          <div class="flex items-center gap-2 mb-1.5">
            <span class="text-sm font-bold text-gray-900">{{ addr.name }}</span>
            <span class="text-sm text-gray-500">{{ addr.phoneNumber }}</span>
          </div>
          <p class="text-sm text-gray-600 leading-5">
            {{ addr.province }} {{ addr.city }} {{ addr.region }}
          </p>
          <p class="text-sm text-gray-500 mt-0.5">{{ addr.detailAddress }}</p>
        </div>

        <!-- 操作按钮 -->
        <div class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100/60">
          <button
            v-if="addr.defaultStatus !== 1"
            class="text-xs text-gray-500 hover:text-red-600 transition-colors"
            @click="handleSetDefault(addr.id)"
          >设为默认</button>
          <button class="text-xs text-gray-500 hover:text-blue-600 transition-colors" @click="openEditDialog(addr)">编辑</button>
          <button class="text-xs text-gray-500 hover:text-red-600 transition-colors" @click="handleDelete(addr.id)">删除</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== Dialog 弹窗 ===== -->
  <Teleport to="body">
    <div
      v-if="showDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      @click.self="closeDialog"
    >
      <div class="bg-white rounded-xl shadow-2xl w-[520px] mx-4 overflow-hidden animate-[fadeIn_0.2s_ease-out]">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h3 class="text-base font-bold text-gray-900">{{ dialogTitle }}</h3>
          <button class="text-gray-400 hover:text-gray-600 transition-colors" @click="closeDialog">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 表单 -->
        <div class="px-6 py-5 space-y-4">
          <!-- 收货人 + 手机号 -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">收货人 <span class="text-red-500">*</span></label>
              <input
                v-model="editingAddress.name"
                type="text"
                placeholder="姓名"
                :class="['w-full h-10 px-3 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent', formErrors.name ? 'border-red-300' : 'border-gray-300']"
              />
              <p v-if="formErrors.name" class="text-xs text-red-500 mt-1">{{ formErrors.name }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">手机号 <span class="text-red-500">*</span></label>
              <input
                v-model="editingAddress.phoneNumber"
                type="tel"
                maxlength="11"
                placeholder="11位手机号"
                :class="['w-full h-10 px-3 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent', formErrors.phoneNumber ? 'border-red-300' : 'border-gray-300']"
              />
              <p v-if="formErrors.phoneNumber" class="text-xs text-red-500 mt-1">{{ formErrors.phoneNumber }}</p>
            </div>
          </div>

          <!-- 省市区联动级联选择器 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">所在地区 <span class="text-red-500">*</span></label>
            <div class="grid grid-cols-3 gap-3">
              <!-- 省份 -->
              <select
                v-model="selectedProvince"
                class="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white"
                @change="onProvinceChange"
              >
                <option value="">请选择省份</option>
                <option v-for="p in provinceList" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
              <!-- 城市 -->
              <select
                v-model="selectedCity"
                class="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white"
                @change="onCityChange"
              >
                <option value="">请选择城市</option>
                <option v-for="c in getCityList(selectedProvince)" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
              <!-- 区县 -->
              <select
                v-model="selectedRegion"
                class="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white"
              >
                <option value="">请选择区县</option>
                <option v-for="r in getRegionList(selectedProvince, selectedCity)" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
            </div>
            <p v-if="formErrors.region" class="text-xs text-red-500 mt-1">{{ formErrors.region }}</p>
          </div>

          <!-- 详细地址 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">详细地址 <span class="text-red-500">*</span></label>
            <textarea
              v-model="editingAddress.detailAddress"
              rows="2"
              placeholder="街道、门牌号、楼层等"
              :class="['w-full px-3 py-2 border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent', formErrors.detailAddress ? 'border-red-300' : 'border-gray-300']"
            />
            <p v-if="formErrors.detailAddress" class="text-xs text-red-500 mt-1">{{ formErrors.detailAddress }}</p>
          </div>

          <!-- 设为默认 -->
          <label class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              v-model="editingAddress.defaultStatus"
              type="checkbox"
              :true-value="1"
              :false-value="0"
              class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
            />
            <span>设为默认地址</span>
          </label>
        </div>

        <!-- 底部按钮 -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50">
          <button class="h-10 px-6 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-100 transition-colors" @click="closeDialog">取消</button>
          <button class="h-10 px-6 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors" @click="handleSave">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95) translateY(-10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
