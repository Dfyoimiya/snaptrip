<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import { getReturnReasonListAPI, returnReasonCreateAPI, returnReasonUpdateAPI, returnReasonDeleteByIdsAPI, returnReasonUpdateStatusAPI } from '@/apis/returnReason'
import type { OmsOrderReturnReason } from '@/types/returnReason'

const listQuery = ref({ pageNum: 1, pageSize: 10 })

const list = ref<OmsOrderReturnReason[]>([])
const total = ref(0)
const listLoading = ref(false)
const multipleSelection = ref<OmsOrderReturnReason[]>([])
const operateType = ref<number>()

const defaultReturnReason = { name: '', sort: 0, status: 1 }
const dialogVisible = ref(false)
const returnReason = ref(Object.assign({}, defaultReturnReason))
const operateReasonId = ref<number | undefined>()
const operateOptions = ref([{ label: '删除', value: 1 }])

const fetchData = async () => {
  listLoading.value = true
  try {
    const res = await getReturnReasonListAPI({
      page: listQuery.value.pageNum,
      page_size: listQuery.value.pageSize,
    })
    list.value = res.items || []
    total.value = res.total || 0
  } catch {
    list.value = []
    total.value = 0
  } finally {
    listLoading.value = false
  }
}

onMounted(() => { fetchData() })

const handleAdd = () => { dialogVisible.value = true; operateReasonId.value = undefined; returnReason.value = Object.assign({}, defaultReturnReason) }

const handleConfirm = async () => {
  if (!returnReason.value.name) { ElMessage({ message: '请输入原因类型', type: 'warning', duration: 1000 }); return }
  try {
    if (!operateReasonId.value) {
      await returnReasonCreateAPI(returnReason.value)
      ElMessage({ message: '添加成功！', type: 'success', duration: 1000 })
    } else {
      await returnReasonUpdateAPI(operateReasonId.value, returnReason.value)
      ElMessage({ message: '修改成功！', type: 'success', duration: 1000 })
    }
    dialogVisible.value = false
    operateReasonId.value = undefined
    fetchData()
  } catch {
    ElMessage({ message: '操作失败', type: 'error', duration: 1000 })
  }
}

const handleUpdate = (_index: number, row: OmsOrderReturnReason) => { dialogVisible.value = true; operateReasonId.value = row.id; returnReason.value = { name: row.name, sort: row.sort, status: row.status } }

const handleDelete = (_index: number, row: OmsOrderReturnReason) => { deleteReasonMethod([row.id!]) }

const handleSelectionChange = (val: OmsOrderReturnReason[]) => { multipleSelection.value = val }

const handleStatusChange = async (_index: number, row: OmsOrderReturnReason) => {
  try {
    await returnReasonUpdateStatusAPI({ ids: String(row.id), status: row.status! })
    ElMessage({ message: '状态修改成功', type: 'success' })
  } catch {
    ElMessage({ message: '状态修改失败', type: 'error' })
  }
}

const handleBatchOperate = () => {
  if (!multipleSelection.value || multipleSelection.value.length < 1) { ElMessage({ message: '请选择要操作的条目', type: 'warning', duration: 1000 }); return }
  if (operateType.value === 1) deleteReasonMethod(multipleSelection.value.map(item => item.id!))
}

const handleSizeChange = (val: number) => { listQuery.value.pageNum = 1; listQuery.value.pageSize = val; fetchData() }
const handleCurrentChange = (val: number) => { listQuery.value.pageNum = val; fetchData() }

const deleteReasonMethod = async (ids: number[]) => {
  await ElMessageBox.confirm('是否要进行该删除操作?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  try {
    await returnReasonDeleteByIdsAPI({ ids: ids.join(',') })
    listQuery.value.pageNum = 1
    fetchData()
    ElMessage({ message: '删除成功！', type: 'success', duration: 1000 })
  } catch {
    ElMessage({ message: '删除失败', type: 'error', duration: 1000 })
  }
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
