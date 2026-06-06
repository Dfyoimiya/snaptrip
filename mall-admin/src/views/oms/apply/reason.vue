<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'

const listQuery = ref({ pageNum: 1, pageSize: 10 })

const allList = ref([
  { id: 1, name: '质量问题', sort: 1, status: 1, createTime: '2024-01-01T00:00:00' },
  { id: 2, name: '商品描述不符', sort: 2, status: 1, createTime: '2024-01-02T00:00:00' },
  { id: 3, name: '不想要了', sort: 3, status: 1, createTime: '2024-01-03T00:00:00' },
  { id: 4, name: '其他原因', sort: 4, status: 1, createTime: '2024-01-04T00:00:00' },
  { id: 5, name: '价格问题', sort: 5, status: 0, createTime: '2024-01-05T00:00:00' },
  { id: 6, name: '物流问题', sort: 6, status: 1, createTime: '2024-01-06T00:00:00' },
  { id: 7, name: '颜色/尺码/规格不符', sort: 7, status: 1, createTime: '2024-01-07T00:00:00' },
  { id: 8, name: '少件/漏发', sort: 8, status: 1, createTime: '2024-01-08T00:00:00' },
  { id: 9, name: '包装破损', sort: 9, status: 1, createTime: '2024-01-09T00:00:00' },
  { id: 10, name: '功能故障', sort: 10, status: 0, createTime: '2024-01-10T00:00:00' },
])

const list = ref([...allList.value])
const total = ref(allList.value.length)
const listLoading = ref(false)
const multipleSelection = ref<any[]>([])
const operateType = ref<number>()

const defaultReturnReason = { name: '', sort: 0, status: 1 }
const dialogVisible = ref(false)
const returnReason = ref(Object.assign({}, defaultReturnReason))
const operateReasonId = ref<number>()
const operateOptions = ref([{ label: '删除', value: 1 }])

const getList = () => {
  listLoading.value = true
  let result = [...allList.value]
  total.value = result.length
  const start = (listQuery.value.pageNum - 1) * listQuery.value.pageSize
  list.value = result.slice(start, start + listQuery.value.pageSize)
  listLoading.value = false
}
onMounted(() => { getList() })

const handleAdd = () => { dialogVisible.value = true; operateReasonId.value = undefined; returnReason.value = Object.assign({}, defaultReturnReason) }

const handleConfirm = () => {
  if (!returnReason.value.name) { ElMessage({ message: '请输入原因类型', type: 'warning', duration: 1000 }); return }
  if (!operateReasonId.value) {
    allList.value.unshift({ ...returnReason.value, id: Date.now(), createTime: new Date().toISOString() })
    ElMessage({ message: '添加成功！', type: 'success', duration: 1000 })
  } else {
    const idx = allList.value.findIndex(item => item.id === operateReasonId.value)
    if (idx > -1) allList.value[idx] = { ...allList.value[idx], ...returnReason.value }
    ElMessage({ message: '修改成功！', type: 'success', duration: 1000 })
  }
  dialogVisible.value = false
  operateReasonId.value = undefined
  getList()
}

const handleUpdate = (_index: number, row: any) => { dialogVisible.value = true; operateReasonId.value = row.id; returnReason.value = { name: row.name, sort: row.sort, status: row.status } }

const handleDelete = (_index: number, row: any) => { deleteReasonMethod([row.id]) }

const handleSelectionChange = (val: any[]) => { multipleSelection.value = val }

const handleStatusChange = (_index: number, row: any) => { ElMessage({ message: '状态修改成功', type: 'success' }) }

const handleBatchOperate = () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) { ElMessage({ message: '请选择要操作的条目', type: 'warning', duration: 1000 }); return }
  if (operateType.value === 1) deleteReasonMethod(multipleSelection.value.map(item => item.id))
}

const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; getList() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; getList() }

const deleteReasonMethod = async (ids: number[]) => {
  await ElMessageBox.confirm('是否要进行该删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  allList.value = allList.value.filter(item => !ids.includes(item.id))
  listQuery.value.pageNum = 1
  getList()
  ElMessage({ message: '删除成功！', type: 'success', duration: 1000 })
}
</script>

<template>
  <div class="app-container">
    <el-card class="operate-container" shadow="never">
      <el-icon class="el-icon-middle"><Tickets /></el-icon>
      <span>数据列表</span>
      <el-button @click="handleAdd" class="btn-add" style="float: right">添加</el-button>
    </el-card>
    <div class="table-container">
      <el-table ref="returnReasonTable" :data="list" style="width: 100%;" @selection-change="handleSelectionChange" v-loading="listLoading" border>
        <el-table-column type="selection" width="60" align="center"></el-table-column>
        <el-table-column label="编号" width="80" align="center">
          <template #default="scope">{{ scope.row.id }}</template>
        </el-table-column>
        <el-table-column label="原因类型" align="center">
          <template #default="scope">{{ scope.row.name }}</template>
        </el-table-column>
        <el-table-column label="排序" width="100" align="center">
          <template #default="scope">{{ scope.row.sort }}</template>
        </el-table-column>
        <el-table-column label="是否可用" align="center">
          <template #default="scope">
            <el-switch v-model="scope.row.status" @change="handleStatusChange(scope.$index, scope.row)" :active-value="1" :inactive-value="0"></el-switch>
          </template>
        </el-table-column>
        <el-table-column label="添加时间" width="180" align="center">
          <template #default="scope">{{ formatDateTime(scope.row.createTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="scope">
            <el-button size="small" @click="handleUpdate(scope.$index, scope.row)">编辑</el-button>
            <el-button size="small" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="batch-operate-container">
      <el-select v-model="operateType" placeholder="批量操作">
        <el-option v-for="item in operateOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
      </el-select>
      <el-button style="margin-left: 20px" class="search-button" @click="handleBatchOperate" type="primary">确定</el-button>
    </div>
    <div class="pagination-container">
      <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
        layout="total, sizes,prev, pager, next,jumper" v-model:current-page="listQuery.pageNum"
        :page-size="listQuery.pageSize" :page-sizes="[5, 10, 15]" :total="total"></el-pagination>
    </div>
    <el-dialog title="添加退货原因" v-model="dialogVisible" width="30%">
      <el-form :model="returnReason" label-width="150px">
        <el-form-item label="原因类型：">
          <el-input v-model="returnReason.name" class="input-width"></el-input>
        </el-form-item>
        <el-form-item label="排序：">
          <el-input v-model="returnReason.sort" class="input-width"></el-input>
        </el-form-item>
        <el-form-item label="是否启用：">
          <el-switch v-model="returnReason.status" :active-value="1" :inactive-value="0"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取 消</el-button>
          <el-button type="primary" @click="handleConfirm">确 定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.input-width { width: 80% }
.batch-operate-container { display: inline-block; margin-top: 12px; }
.pagination-container { display: inline-block; float: right; margin-top: 12px; }
.el-icon-middle { vertical-align: middle; margin-right: 6px; }
</style>
