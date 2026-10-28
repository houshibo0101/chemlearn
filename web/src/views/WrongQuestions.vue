<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div class="page-head">
      <div>
        <div class="page-head__title">错题本</div>
        <div class="page-head__desc">按错误次数排序，可导出成 PDF / Excel 打印复习</div>
      </div>
      <div class="page-head__actions">
        <el-button type="primary" :icon="VideoPlay" @click="repractice">一键重练错题</el-button>
        <el-button :icon="Printer" @click="exportPDF">导出 PDF</el-button>
        <el-button :icon="Download" @click="exportExcel">导出 Excel</el-button>
      </div>
    </div>

    <el-card v-if="list.length === 0 && !loading" class="page-card">
      <el-empty description="还没有错题，继续加油！" />
    </el-card>

    <el-card v-for="item in list" :key="item.id" class="page-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
        <div>
          <el-tag type="danger" size="small">错 {{ item.wrong_count }} 次</el-tag>
          <span style="margin-left:8px;font-size:12px;color:var(--text-placeholder);">最后错误：{{ formatTime(item.last_wrong_at) }}</span>
        </div>
        <el-button text type="danger" size="small" @click="removeItem(item.id)">删除</el-button>
      </div>

      <div style="font-size:15px;font-weight:500;margin-bottom:8px;">
        <el-tag size="small" type="info" style="margin-right:8px;">{{ item.question_code || 'Q' + String(item.question_id).padStart(4, '0') }}</el-tag>
        {{ item.question_title }}
      </div>
      <div v-if="item.question_content" style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;white-space:pre-wrap;">{{ item.question_content }}</div>

      <el-descriptions :column="1" size="small" border style="margin-bottom:10px;">
        <el-descriptions-item label="你的答案">{{ item.user_answer || '未作答' }}</el-descriptions-item>
        <el-descriptions-item label="正确答案">{{ item.correct_answer }}</el-descriptions-item>
        <el-descriptions-item v-if="item.analysis" label="解析">{{ item.analysis }}</el-descriptions-item>
      </el-descriptions>

      <!-- AI讲解 / AI变式 -->
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <el-button type="primary" size="small" :icon="ChatDotRound" @click="toggleAI(item.id)">
          {{ aiVisible[item.id] ? '收起AI讲解' : '🤖 AI讲解/追问' }}
        </el-button>
        <el-button type="success" size="small" :icon="MagicStick" @click="openVariants(item)">
          🧬 AI出变式题
        </el-button>
      </div>

      <div v-if="aiVisible[item.id]" style="margin-top:12px;padding:12px;background:var(--bg-tertiary);border-radius:8px;">
        <div v-if="aiLoading[item.id]" style="text-align:center;padding:20px;color:var(--text-placeholder);">
          <el-icon class="is-loading" style="font-size:24px;"><Loading /></el-icon>
          <div style="margin-top:8px;font-size:13px;">AI正在思考...</div>
        </div>
        <div v-else-if="aiReply[item.id]" class="markdown-body" v-html="renderMarkdown(aiReply[item.id])"></div>

        <!-- 追问 -->
        <div style="display:flex;gap:8px;margin-top:10px;">
          <el-input v-model="followUp[item.id]" placeholder="输入追问内容..." size="small" @keyup.enter="askFollowUp(item)" />
          <el-button type="primary" size="small" @click="askFollowUp(item)">追问</el-button>
        </div>
      </div>
    </el-card>

    <div v-if="list.length > 0" style="text-align:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, prev, pager, next"
        @current-change="loadList"
      />
    </div>

    <!-- AI变式题弹窗 -->
    <el-dialog v-model="variantDialog" title="🧬 AI 变式题（举一反三）" width="640px" :close-on-click-modal="false">
      <div v-if="variantLoading" style="text-align:center;padding:40px 0;">
        <el-icon class="is-loading" style="font-size:30px;color:var(--brand-600);"><Loading /></el-icon>
        <div style="margin-top:10px;font-size:13px;color:var(--text-secondary);">AI 正在根据这道错题生成变式题...</div>
      </div>
      <template v-else>
        <div v-if="variantOriginal" style="margin-bottom:14px;padding:10px 14px;background:var(--bg-tertiary);border-radius:8px;font-size:13px;color:var(--text-secondary);">
          原题：<b style="color:var(--text-primary);">{{ variantOriginal.title }}</b>
          <span v-if="variantOriginal.knowledge_point" style="margin-left:8px;">（{{ variantOriginal.knowledge_point }}）</span>
        </div>
        <div v-for="(v, i) in variants" :key="i" class="variant-item">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <el-tag size="small" type="success">变式 {{ i + 1 }}</el-tag>
            <el-tag size="small" type="info">{{ diffText(v.difficulty) }}</el-tag>
          </div>
          <div style="font-size:14px;line-height:1.7;white-space:pre-wrap;">{{ v.title }}</div>
          <div v-if="v.options && v.options.length" style="margin-top:8px;">
            <div v-for="opt in v.options" :key="opt.key" style="font-size:13.5px;color:var(--text-secondary);line-height:1.8;">
              <b>{{ opt.key }}.</b> {{ opt.text }}
            </div>
          </div>
          <el-collapse style="margin-top:8px;border:none;">
            <el-collapse-item title="查看答案与解析">
              <div style="font-size:13.5px;"><b style="color:var(--success-color,#10B981);">答案：</b>{{ v.answer || '（AI未给出）' }}</div>
              <div v-if="v.analysis" style="font-size:13.5px;margin-top:6px;"><b>解析：</b>{{ v.analysis }}</div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-if="variants.length === 0" style="text-align:center;color:var(--text-secondary);padding:20px 0;font-size:13px;">
          没有生成有效变式题，请重试
        </div>
        <div style="text-align:center;margin-top:14px;">
          <el-button type="primary" plain size="small" :loading="variantLoading" @click="generateVariants">再生成一组</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, ChatDotRound, Loading, Printer, VideoPlay, MagicStick } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'

const router = useRouter()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const aiVisible = reactive({})
const aiLoading = reactive({})
const aiReply = reactive({})
const followUp = reactive({})

// ===== AI 变式题 =====
const variantDialog = ref(false)
const variantLoading = ref(false)
const variants = ref([])
const variantOriginal = ref(null)
const variantWrongId = ref(null)

const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)

const openVariants = (item) => {
  variantWrongId.value = item.id
  variantOriginal.value = { title: item.question_title, knowledge_point: null }
  variants.value = []
  variantDialog.value = true
  generateVariants()
}

const generateVariants = async () => {
  if (!variantWrongId.value) return
  variantLoading.value = true
  try {
    const res = await api.post(`/wrong-questions/${variantWrongId.value}/variants`, null, { params: { count: 3 } })
    variants.value = res.variants || []
    if (res.original) variantOriginal.value = res.original
  } catch {
    variants.value = []
  } finally {
    variantLoading.value = false
  }
}

// ===== 一键重练 =====
const repractice = () => {
  if (total.value === 0) {
    ElMessage.info('错题本还是空的，先去刷题吧！')
    return
  }
  router.push('/practice?source=wrong')
}

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const loadList = async () => {
  loading.value = true
  try {
    const res = await api.get('/wrong-questions', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const toggleAI = async (id) => {
  aiVisible[id] = !aiVisible[id]
  if (aiVisible[id] && !aiReply[id]) {
    await askAI(id, null)
  }
}

const askAI = async (id, followUpText) => {
  aiLoading[id] = true
  try {
    const res = await api.post('/wrong-questions/ai-explain', {
      wrong_question_id: id,
      follow_up: followUpText,
    })
    aiReply[id] = res.reply
  } catch {
  } finally {
    aiLoading[id] = false
  }
}

const askFollowUp = (item) => {
  const text = followUp[item.id]?.trim()
  if (!text) return
  askAI(item.id, text)
  followUp[item.id] = ''
}

const removeItem = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这条错题记录吗？', '提示', { type: 'warning' })
    await api.delete(`/wrong-questions/${id}`)
    ElMessage.success('已删除')
    loadList()
  } catch {}
}

const exportPDF = async () => {
  try {
    ElMessage.info('正在生成PDF...')
    // 获取全部错题
    const res = await api.get('/wrong-questions', { params: { page: 1, page_size: 500 } })
    const items = res.items || []
    if (items.length === 0) {
      ElMessage.warning('没有错题可导出')
      return
    }

    const now = new Date().toLocaleString('zh-CN')
    let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>错题本导出</title>
    <style>
      body { font-family: 'Microsoft YaHei', sans-serif; padding: 30px; color: #333; }
      h1 { text-align: center; font-size: 22px; margin-bottom: 6px; }
      .subtitle { text-align: center; color: #888; font-size: 12px; margin-bottom: 24px; }
      .item { page-break-inside: avoid; margin-bottom: 20px; padding: 14px; border: 1px solid #ddd; border-radius: 6px; }
      .item-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #888; }
      .item-title { font-size: 15px; font-weight: 600; margin-bottom: 8px; line-height: 1.6; }
      .item-content { font-size: 13px; color: #555; margin-bottom: 8px; white-space: pre-wrap; line-height: 1.6; }
      .row { font-size: 13px; margin: 4px 0; line-height: 1.6; }
      .row label { font-weight: 600; color: #333; }
      .wrong-ans { color: var(--danger-color); }
      .correct-ans { color: var(--success-color); }
      .analysis { color: var(--text-secondary); background: var(--bg-tertiary); padding: 8px; border-radius: 4px; margin-top: 6px; }
      @media print { body { padding: 15px; } .item { border-color: #ccc; } }
    </style></head><body>
    <h1>📕 化学错题本</h1>
    <div class="subtitle">共 ${items.length} 道错题 · 导出时间：${now}</div>`

    items.forEach((item, idx) => {
      html += `<div class="item">
        <div class="item-header"><span>第 ${idx + 1} 题 · 错误 ${item.wrong_count || 1} 次</span><span>${formatTime(item.last_wrong_at)}</span></div>
        <div class="item-title">${item.question_title || ''}</div>`
      if (item.question_content) html += `<div class="item-content">${item.question_content}</div>`
      html += `<div class="row"><label>你的答案：</label><span class="wrong-ans">${item.user_answer || '未作答'}</span></div>
        <div class="row"><label>正确答案：</label><span class="correct-ans">${item.correct_answer || ''}</span></div>`
      if (item.analysis) html += `<div class="row analysis"><label>解析：</label>${item.analysis}</div>`
      html += `</div>`
    })

    html += `</body></html>`

    const printWindow = window.open('', '_blank')
    printWindow.document.write(html)
    printWindow.document.close()
    printWindow.onload = () => {
      setTimeout(() => {
        printWindow.print()
      }, 300)
    }
    ElMessage.success('PDF已生成，请在打印窗口中选择"另存为PDF"')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const exportExcel = () => {
  const token = localStorage.getItem('token')
  const a = document.createElement('a')
  a.href = `/api/v1/wrong-questions/export/excel`
  a.style.display = 'none'
  // 带token的方式：用fetch
  fetch('/chem/api/v1/wrong-questions/export/excel', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    a.href = url
    a.download = '错题记录.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  })
}

onMounted(loadList)
</script>
