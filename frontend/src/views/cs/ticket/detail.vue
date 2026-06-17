<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Promotion } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/datetime'
import {
  getTicketDetailAPI,
  updateTicketAPI,
  assignTicketAPI,
  resolveTicketAPI,
  getTicketMessagesAPI,
  sendTicketMessageAPI,
  getTicketStreamUrl,
} from '@/apis/cs'
import type { CsTicket, CsMessage } from '@/types/cs'

const route = useRoute()
const router = useRouter()

const ticketId = route.params.id as string

const ticket = ref<CsTicket | null>(null)
const messages = ref<CsMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const sending = ref(false)
const resolving = ref(false)

const resolveForm = ref({ resolution: '', satisfactionScore: undefined as number | undefined })
const resolveDialogVisible = ref(false)

let eventSource: EventSource | null = null

// ── Load ticket ──
const loadTicket = async () => {
  try {
    const res = await getTicketDetailAPI(ticketId)
    ticket.value = res.data as any || null
  } catch {
    ElMessage.error('获取工单详情失败')
  }
}

// ── Load messages ──
const loadMessages = async () => {
  try {
    const res = await getTicketMessagesAPI(ticketId, 100)
    messages.value = (res.data as any)?.messages || []
    await nextTick()
    scrollToBottom()
  } catch {
    // silent
  }
}

// ── SSE stream ──
const connectStream = () => {
  const url = getTicketStreamUrl(ticketId)
  eventSource = new EventSource(url)

  eventSource.addEventListener('connected', () => {
    // connected
  })

  eventSource.addEventListener('new_message', (e) => {
    try {
      const msg = JSON.parse(e.data) as CsMessage
      // Avoid duplicates
      if (!messages.value.find(m => m.id === msg.id)) {
        messages.value.push(msg)
        nextTick(() => scrollToBottom())
      }
    } catch { /* ignore parse errors */ }
  })

  eventSource.addEventListener('error', () => {
    // Auto-reconnect built into EventSource
  })
}

// ── Send message ──
const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text) return
  sending.value = true
  try {
    await sendTicketMessageAPI(ticketId, text)
    inputText.value = ''
  } catch {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

// ── Actions ──
const handleClaim = async () => {
  try {
    await assignTicketAPI(ticketId, undefined, 'claim')
    ElMessage.success('已认领工单')
    await loadTicket()
  } catch {
    ElMessage.error('认领失败')
  }
}

const handleAssign = async () => {
  try {
    const { value: agentId } = await ElMessageBox.prompt('请输入坐席 ID（留空取消指派）', '指派坐席')
    const action = agentId ? 'assign' : 'unassign'
    await assignTicketAPI(ticketId, agentId || undefined, action)
    ElMessage.success(action === 'unassign' ? '已取消指派' : '已指派')
    await loadTicket()
  } catch { /* cancelled */ }
}

const handleResolve = () => {
  resolveForm.value = { resolution: '', satisfactionScore: undefined }
  resolveDialogVisible.value = true
}

const confirmResolve = async () => {
  if (!resolveForm.value.resolution.trim()) {
    ElMessage.warning('请填写处理结果')
    return
  }
  resolving.value = true
  try {
    await resolveTicketAPI(ticketId, resolveForm.value.resolution, resolveForm.value.satisfactionScore)
    ElMessage.success('工单已解决')
    resolveDialogVisible.value = false
    await loadTicket()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    resolving.value = false
  }
}

const handleUpdateStatus = async (status: string) => {
  try {
    await updateTicketAPI(ticketId, { status })
    ElMessage.success('状态已更新')
    await loadTicket()
  } catch {
    ElMessage.error('更新失败')
  }
}

// ── Helpers ──
const scrollToBottom = () => {
  const el = document.getElementById('chat-messages')
  if (el) el.scrollTop = el.scrollHeight
}

const statusText = (s?: string) => {
  const map: Record<string, string> = { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }
  return map[s || ''] || s || '-'
}

const priorityText = (p?: string) => {
  const map: Record<string, string> = { normal: '普通', urgent: '紧急', critical: '严重' }
  return map[p || ''] || p || '-'
}

const goBack = () => router.push({ name: 'csTickets' })

onMounted(async () => {
  loading.value = true
  await Promise.all([loadTicket(), loadMessages()])
  loading.value = false
  connectStream()
})

onUnmounted(() => {
  eventSource?.close()
})
</script>

<template>
  <div class="cs-detail-container" v-loading="loading">
    <!-- Header -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="goBack">返回列表</el-button>
      <span class="ticket-title">{{ ticket?.title || '工单详情' }}</span>
      <div class="header-actions">
        <template v-if="ticket?.status === 'open' && !ticket?.assignedAgentId">
          <el-button type="primary" size="small" @click="handleClaim">认领</el-button>
        </template>
        <el-button size="small" @click="handleAssign">指派</el-button>
        <template v-if="ticket?.status !== 'resolved' && ticket?.status !== 'closed'">
          <el-button type="success" size="small" @click="handleResolve">解决</el-button>
        </template>
      </div>
    </div>

    <div class="detail-body">
      <!-- Left: ticket info -->
      <div class="info-panel">
        <el-card header="工单信息" size="small">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="ID">{{ ticket?.id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="ticket?.status === 'open' ? 'danger' : ticket?.status === 'in_progress' ? 'warning' : 'success'" size="small">
                {{ statusText(ticket?.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="优先级">
              <el-tag :type="ticket?.priority === 'critical' ? 'danger' : ticket?.priority === 'urgent' ? 'warning' : 'info'" size="small">
                {{ priorityText(ticket?.priority) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="类型">{{ ticket?.type }}</el-descriptions-item>
            <el-descriptions-item label="关联订单">{{ ticket?.orderId || '无' }}</el-descriptions-item>
            <el-descriptions-item label="指派人">{{ ticket?.assignedAgentId || '未指派' }}</el-descriptions-item>
            <el-descriptions-item label="SLA 截止">{{ formatDateTime(ticket?.slaDeadline) || '无' }}</el-descriptions-item>
            <el-descriptions-item label="首次响应">{{ formatDateTime(ticket?.firstResponseAt) || '无' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(ticket?.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="1">
              <div style="white-space: pre-wrap;">{{ ticket?.description || '无' }}</div>
            </el-descriptions-item>
            <el-descriptions-item v-if="ticket?.resolution" label="处理结果" :span="1">
              <div style="white-space: pre-wrap;">{{ ticket?.resolution }}</div>
            </el-descriptions-item>
          </el-descriptions>

          <div class="status-actions" v-if="ticket?.status !== 'resolved' && ticket?.status !== 'closed'">
            <el-divider />
            <div style="font-size: 12px; color: #909399; margin-bottom: 8px;">快捷操作</div>
            <el-button size="small" v-if="ticket?.status === 'open'" @click="handleUpdateStatus('in_progress')">标记处理中</el-button>
          </div>
        </el-card>
      </div>

      <!-- Right: chat -->
      <div class="chat-panel">
        <el-card header="对话" size="small" class="chat-card">
          <div id="chat-messages" class="chat-messages">
            <div v-if="messages.length === 0" class="empty-chat">暂无消息</div>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="chat-bubble"
              :class="{
                'chat-user': msg.senderType === 'user',
                'chat-agent': msg.senderType === 'agent',
                'chat-system': msg.senderType === 'system',
              }"
            >
              <div class="bubble-label">{{ msg.senderType === 'user' ? '用户' : msg.senderType === 'agent' ? '坐席' : '系统' }}</div>
              <div class="bubble-content" :class="{ 'system-event': msg.senderType === 'system' }">{{ msg.content }}</div>
              <div class="bubble-time">{{ formatDateTime(msg.createdAt) }}</div>
            </div>
          </div>

          <div class="chat-input" v-if="ticket?.status !== 'resolved' && ticket?.status !== 'closed'">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="输入回复… 支持 Markdown"
              @keyup.enter.ctrl="sendMessage"
            />
            <el-button
              type="primary"
              size="small"
              :loading="sending"
              :disabled="!inputText.trim()"
              style="margin-top: 8px;"
              @click="sendMessage"
            >
              发送 (Ctrl+Enter)
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Resolve Dialog -->
    <el-dialog v-model="resolveDialogVisible" title="解决工单" width="500px">
      <el-form :model="resolveForm" label-width="100px">
        <el-form-item label="处理结果" required>
          <el-input v-model="resolveForm.resolution" type="textarea" :rows="4" placeholder="请描述处理结果" />
        </el-form-item>
        <el-form-item label="满意度">
          <el-rate v-model="resolveForm.satisfactionScore" :max="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resolving" @click="confirmResolve">确认解决</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cs-detail-container {
  padding: 16px;
  height: calc(100vh - 84px);
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.ticket-title {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.detail-body {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.info-panel {
  width: 380px;
  flex-shrink: 0;
  overflow-y: auto;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.empty-chat {
  color: #909399;
  text-align: center;
  padding: 40px 0;
}

.chat-bubble {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 80%;
}

.chat-user {
  background: #ecf5ff;
  margin-right: auto;
}

.chat-agent {
  background: #f0f9eb;
  margin-left: auto;
}

.chat-system {
  background: #fdf6ec;
  margin: 0 auto;
  text-align: center;
  max-width: 90%;
}

.bubble-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
}

.bubble-content {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.bubble-content.system-event {
  font-size: 12px;
  color: #e6a23c;
}

.bubble-time {
  font-size: 10px;
  color: #c0c4cc;
  margin-top: 2px;
  text-align: right;
}

.chat-input {
  border-top: 1px solid #ebeef5;
  padding-top: 8px;
  margin-top: 8px;
}

.status-actions {
  margin-top: 8px;
}
</style>
