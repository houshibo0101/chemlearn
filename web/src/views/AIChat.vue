<template>
  <div class="app-container" style="padding-bottom:80px;display:flex;flex-direction:column;height:calc(100vh - 60px);">
    <div class="page-head" style="margin-bottom:14px;">
      <div class="page-head__title">🤖 AI 化学问答</div>
      <div style="display:flex;align-items:center;gap:10px;">
        <el-tooltip :content="`已用 ${stats.usage_percent}%（${formatBytes(stats.total_bytes)} / 1MB），超出后自动删除最早对话`">
          <span class="quota-chip">💾 {{ formatBytes(stats.total_bytes) }} / 1MB</span>
        </el-tooltip>
        <el-button size="small" type="danger" plain :icon="Delete" @click="clearHistory" :disabled="messages.length === 0">清空对话</el-button>
      </div>
    </div>

    <!-- 快捷问题 -->
    <div style="margin-bottom:14px;display:flex;gap:8px;flex-wrap:wrap;">
      <el-tag v-for="q in quickQuestions" :key="q" class="quick-tag" effect="plain" @click="sendQuick(q)">{{ q }}</el-tag>
    </div>

    <!-- 消息区 -->
    <div ref="chatBox" class="chat-box">
      <div v-if="messages.length === 0 && !loading" class="empty-state">
        <div class="empty-state__icon">💬</div>
        <p style="margin-top:6px;">有什么化学问题想问我吗？</p>
        <p style="font-size:12px;margin-top:4px;color:var(--text-disabled);">对话会自动保存，刷新页面不丢失</p>
      </div>
      <div v-for="(msg, idx) in messages" :key="idx" class="chat-message" :class="msg.role">
        <div class="chat-avatar" :class="msg.role">{{ msg.role === 'user' ? '🧑' : '🤖' }}</div>
        <div class="chat-bubble" :class="msg.role">
          <!-- AI 消息渲染 Markdown -->
          <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
          <!-- 用户消息纯文本 -->
          <div v-else style="white-space:pre-wrap;word-break:break-word;">{{ msg.content }}</div>
        </div>
      </div>
      <div v-if="loading" class="chat-message">
        <div class="chat-avatar ai">🤖</div>
        <div class="chat-bubble ai">
          <el-icon class="is-loading"><Loading /></el-icon> 正在思考...
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="composer">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入你的化学问题...（回车发送，Ctrl+回车换行）"
        @keydown="handleKeydown"
      />
      <el-button type="primary" :loading="loading" class="composer__send" @click="send">发送</el-button>
    </div>
    <div style="font-size:11px;color:var(--text-disabled);margin-top:8px;text-align:center;">回车发送 · Ctrl+回车换行 · 对话自动保存</div>
  </div>
</template>

<style scoped>
.quota-chip {
  font-size: 12px;
  color: var(--text-placeholder);
  cursor: help;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
}
.quick-tag { cursor: pointer; transition: all var(--dur) var(--ease); }
.quick-tag:hover { border-color: var(--brand-400); color: var(--brand-600); background: var(--brand-50); }

.chat-box {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
}

.composer {
  display: flex;
  gap: 10px;
  align-items: stretch;
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.composer:focus-within { border-color: var(--brand-400); box-shadow: var(--shadow-md), var(--ring); }
.composer__send { height: auto; min-width: 86px; }
</style>

<script setup>
import { ref, reactive, nextTick, onMounted } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, ChatDotRound, Delete } from '@element-plus/icons-vue'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const chatBox = ref(null)
const stats = reactive({ total_bytes: 0, total_count: 0, usage_percent: 0 })

const quickQuestions = [
  '什么是氧化还原反应？',
  '化学平衡怎么判断？',
  '有机物命名规则',
  '摩尔质量怎么算？',
]

const formatBytes = (bytes) => {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

const scrollBottom = () => {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

// 键盘事件：回车发送，Ctrl+回车换行
const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey && !e.metaKey) {
    e.preventDefault()
    send()
  }
}

const loadHistory = async () => {
  try {
    const res = await api.get('/ai/history')
    messages.value = res.map(m => ({ role: m.role, content: m.content }))
    scrollBottom()
  } catch (e) {}
}

const loadStats = async () => {
  try {
    const res = await api.get('/ai/history/stats')
    Object.assign(stats, res)
  } catch (e) {}
}

const sendQuick = (q) => {
  input.value = q
  send()
}

const send = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollBottom()
  try {
    const res = await api.post('/ai/chat', { message: text })
    messages.value.push({ role: 'assistant', content: res.reply })
    loadStats()
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '抱歉，AI服务暂时不可用，请稍后重试。' })
  } finally {
    loading.value = false
    scrollBottom()
  }
}

const clearHistory = async () => {
  try {
    await ElMessageBox.confirm('确定清空所有对话历史吗？此操作不可恢复。', '提示', { type: 'warning' })
    await api.delete('/ai/history')
    messages.value = []
    loadStats()
    ElMessage.success('对话已清空')
  } catch (e) {}
}

onMounted(() => {
  loadHistory()
  loadStats()
})
</script>
