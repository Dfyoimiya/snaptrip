<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const defaultOrderSetting = {
  id: 1,
  flashOrderOvertime: 30,
  normalOrderOvertime: 60,
  confirmOvertime: 15,
  finishOvertime: 7,
  commentOvertime: 7,
}

const orderSetting = ref({ ...defaultOrderSetting })
const orderSettingForm = ref<FormInstance>()

const checkTime = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (!value) return callback(new Error('时间不能为空'))
  const intValue = parseInt(value)
  if (!Number.isInteger(intValue)) return callback(new Error('请输入数字值'))
  callback()
}

const rules = ref<FormRules>({
  flashOrderOvertime: { validator: checkTime, trigger: 'blur' },
  normalOrderOvertime: { validator: checkTime, trigger: 'blur' },
  confirmOvertime: { validator: checkTime, trigger: 'blur' },
  finishOvertime: { validator: checkTime, trigger: 'blur' },
  commentOvertime: { validator: checkTime, trigger: 'blur' },
})

const confirm = async () => {
  if (!orderSettingForm.value) return
  const valid = await orderSettingForm.value.validate()
  if (valid) {
    await ElMessageBox.confirm('是否要提交修改?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    ElMessage({
      type: 'success',
      message: '提交成功!',
      duration: 1000,
    })
  } else {
    ElMessage({
      message: '提交参数不合法',
      type: 'warning',
    })
  }
}
</script>

<template>
  <el-card class="form-container" shadow="never">
    <el-form :model="orderSetting" ref="orderSettingForm" :rules="rules" label-width="150px">
      <el-form-item label="秒杀订单超过：" prop="flashOrderOvertime">
        <el-input v-model="orderSetting.flashOrderOvertime" class="input-width">
          <template #append>分</template>
        </el-input>
        <span class="note-margin">未付款，订单自动关闭</span>
      </el-form-item>
      <el-form-item label="正常订单超过：" prop="normalOrderOvertime">
        <el-input v-model="orderSetting.normalOrderOvertime" class="input-width">
          <template #append>分</template>
        </el-input>
        <span class="note-margin">未付款，订单自动关闭</span>
      </el-form-item>
      <el-form-item label="发货超过：" prop="confirmOvertime">
        <el-input v-model="orderSetting.confirmOvertime" class="input-width">
          <template #append>天</template>
        </el-input>
        <span class="note-margin">未收货，订单自动完成</span>
      </el-form-item>
      <el-form-item label="订单完成超过：" prop="finishOvertime">
        <el-input v-model="orderSetting.finishOvertime" class="input-width">
          <template #append>天</template>
        </el-input>
        <span class="note-margin">自动结束交易，不能申请售后</span>
      </el-form-item>
      <el-form-item label="订单完成超过：" prop="commentOvertime">
        <el-input v-model="orderSetting.commentOvertime" class="input-width">
          <template #append>天</template>
        </el-input>
        <span class="note-margin">自动五星好评</span>
      </el-form-item>
      <el-form-item>
        <el-button @click="confirm" type="primary">提交</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.form-container { width: 800px; margin: 20px auto; }
.input-width { width: 50%; }
.note-margin { margin-left: 15px; color: #909399; font-size: 13px; }
</style>
