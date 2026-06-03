<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

// OSS 配置表单
const ossTypes = [
  { label: '阿里云OSS', value: 'aliyun' },
  { label: '腾讯云COS', value: 'tencent' },
  { label: '七牛云Kodo', value: 'qiniu' },
  { label: 'MinIO', value: 'minio' },
  { label: '本地存储', value: 'local' },
]

const form = reactive({
  ossType: 'aliyun',
  // 阿里云
  aliyunEndpoint: 'oss-cn-hangzhou.aliyuncs.com',
  aliyunBucketName: 'mall-admin-images',
  aliyunAccessKeyId: '',
  aliyunAccessKeySecret: '',
  aliyunDomain: 'https://mall-admin-images.oss-cn-hangzhou.aliyuncs.com',
  // 腾讯云
  tencentBucketName: '',
  tencentRegion: 'ap-guangzhou',
  tencentSecretId: '',
  tencentSecretKey: '',
  tencentDomain: '',
  // 七牛云
  qiniuBucketName: '',
  qiniuAccessKey: '',
  qiniuSecretKey: '',
  qiniuDomain: '',
  // MinIO
  minioEndpoint: '',
  minioBucketName: '',
  minioAccessKey: '',
  minioSecretKey: '',
  // 本地
  localPath: '/upload/images',
  localDomain: '',
})

const formRef = ref()
const saving = ref(false)

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  setTimeout(() => {
    ElMessage.success('保存成功')
    saving.value = false
  }, 500)
}

function handleReset() {
  formRef.value?.resetFields()
}

const baseRules = {
  ossType: [{ required: true, message: '请选择存储类型', trigger: 'change' }],
}
</script>

<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>文件存储配置</span>
          <el-tag type="info" size="small">配置对象存储服务，用于存储商品图片、用户头像等文件</el-tag>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="baseRules" label-width="160px" style="max-width: 700px">
        <!-- 存储类型选择 -->
        <el-form-item label="存储服务类型" prop="ossType">
          <el-radio-group v-model="form.ossType">
            <el-radio-button v-for="item in ossTypes" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-divider />

        <!-- 阿里云 OSS -->
        <template v-if="form.ossType === 'aliyun'">
          <el-form-item label="Endpoint">
            <el-input v-model="form.aliyunEndpoint" placeholder="如：oss-cn-hangzhou.aliyuncs.com" />
          </el-form-item>
          <el-form-item label="Bucket名称">
            <el-input v-model="form.aliyunBucketName" placeholder="Bucket名称" />
          </el-form-item>
          <el-form-item label="AccessKey ID">
            <el-input v-model="form.aliyunAccessKeyId" placeholder="AccessKey ID" show-password />
          </el-form-item>
          <el-form-item label="AccessKey Secret">
            <el-input v-model="form.aliyunAccessKeySecret" placeholder="AccessKey Secret" show-password />
          </el-form-item>
          <el-form-item label="自定义域名">
            <el-input v-model="form.aliyunDomain" placeholder="可选，填写后将使用自定义域名访问" />
          </el-form-item>
        </template>

        <!-- 腾讯云 COS -->
        <template v-if="form.ossType === 'tencent'">
          <el-form-item label="Bucket名称">
            <el-input v-model="form.tencentBucketName" placeholder="Bucket名称" />
          </el-form-item>
          <el-form-item label="地域">
            <el-select v-model="form.tencentRegion" placeholder="选择地域" style="width: 100%">
              <el-option label="广州" value="ap-guangzhou" />
              <el-option label="上海" value="ap-shanghai" />
              <el-option label="北京" value="ap-beijing" />
              <el-option label="成都" value="ap-chengdu" />
            </el-select>
          </el-form-item>
          <el-form-item label="SecretId">
            <el-input v-model="form.tencentSecretId" placeholder="SecretId" show-password />
          </el-form-item>
          <el-form-item label="SecretKey">
            <el-input v-model="form.tencentSecretKey" placeholder="SecretKey" show-password />
          </el-form-item>
          <el-form-item label="自定义域名">
            <el-input v-model="form.tencentDomain" placeholder="可选" />
          </el-form-item>
        </template>

        <!-- 七牛云 -->
        <template v-if="form.ossType === 'qiniu'">
          <el-form-item label="Bucket名称">
            <el-input v-model="form.qiniuBucketName" placeholder="Bucket名称" />
          </el-form-item>
          <el-form-item label="AccessKey">
            <el-input v-model="form.qiniuAccessKey" placeholder="AccessKey" show-password />
          </el-form-item>
          <el-form-item label="SecretKey">
            <el-input v-model="form.qiniuSecretKey" placeholder="SecretKey" show-password />
          </el-form-item>
          <el-form-item label="自定义域名">
            <el-input v-model="form.qiniuDomain" placeholder="如：https://cdn.example.com" />
          </el-form-item>
        </template>

        <!-- MinIO -->
        <template v-if="form.ossType === 'minio'">
          <el-form-item label="Endpoint">
            <el-input v-model="form.minioEndpoint" placeholder="如：http://localhost:9000" />
          </el-form-item>
          <el-form-item label="Bucket名称">
            <el-input v-model="form.minioBucketName" placeholder="Bucket名称" />
          </el-form-item>
          <el-form-item label="AccessKey">
            <el-input v-model="form.minioAccessKey" placeholder="AccessKey" />
          </el-form-item>
          <el-form-item label="SecretKey">
            <el-input v-model="form.minioSecretKey" placeholder="SecretKey" show-password />
          </el-form-item>
        </template>

        <!-- 本地存储 -->
        <template v-if="form.ossType === 'local'">
          <el-form-item label="存储路径">
            <el-input v-model="form.localPath" placeholder="如：/upload/images" />
          </el-form-item>
          <el-form-item label="访问域名">
            <el-input v-model="form.localDomain" placeholder="如：https://example.com" />
          </el-form-item>
        </template>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>保存配置
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.app-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
