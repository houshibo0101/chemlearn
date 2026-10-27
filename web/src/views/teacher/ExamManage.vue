<template>
  <div class="exam-manage">
    <div class="page-header">
      <h2>考试管理</h2>
      <el-button type="primary" @click="showCreate = true">+ 创建考试</el-button>
    </div>

    <el-table :data="exams" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="考试标题" />
      <el-table-column prop="duration" label="时长(分)" width="100" />
      <el-table-column prop="total_score" label="总分" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'info'">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" @click="viewRanking(row)" v-if="row.status === 'published'">排名</el-button>
          <el-button size="small" type="success" @click="publish(row)" v-if="row.status === 'draft'">发布</el-button>
          <el-button size="small" type="danger" @click="deleteItem(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建考试弹窗 -->
    <el-dialog v-model="showCreate" title="创建考试" width="700px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="考试标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="考试说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="考试时长(分)"><el-input-number v-model="form.duration" :min="10" :max="300" /></el-form-item>
        <el-form-item label="总分"><el-input-number v-model="form.total_score" :min="10" :max="500" /></el-form-item>
        <el-form-item label="选择班级">
          <el-select v-model="form.class_ids" multiple placeholder="选择考试班级" style="width:100%">
            <el-option v-for="c in myClasses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择题目">
          <el-button @click="openQuestionPicker">已选 {{ form.questions.length }} 题</el-button>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_time" type="datetime" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_time" type="datetime" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createExam">创建</el-button>
      </template>
    </el-dialog>

    <!-- 题目选择弹窗 -->
    <el-dialog v-model="showQuestionPicker" title="选择题目（可设置每题分值）" width="900px">
      <!-- 筛选 -->
      <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;">
        <el-input v-model="qFilter.keyword" placeholder="搜索题目" clearable style="width:180px;" @keyup.enter="searchQuestions" />
        <el-select v-model="qFilter.difficulty" placeholder="难度" clearable style="width:100px;" @change="searchQuestions">
          <el-option label="简单" value="easy" />
          <el-option label="中等" value="medium" />
          <el-option label="困难" value="hard" />
        </el-select>
        <el-select v-model="qFilter.grade" placeholder="学段" clearable style="width:100px;" @change="searchQuestions">
          <el-option label="高一" value="高一" />
          <el-option label="高二" value="高二" />
          <el-option label="高三" value="高三" />
        </el-select>
        <el-button type="primary" @click="searchQuestions">筛选</el-button>
        <span style="margin-left:auto;line-height:32px;color:var(--text-placeholder);font-size:13px;">共 {{ qTotal }} 题，已选 {{ form.questions.length }} 题</span>
      </div>
      <el-table :data="questionList" @selection-change="onQuestionSelect" stripe max-height="400" row-key="id">
        <el-table-column type="selection" width="50" :reserve-selection="true" />
        <el-table-column prop="question_code" label="编号" width="100" />
        <el-table-column prop="title" label="题目" show-overflow-tooltip />
        <el-table-column label="难度" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="diffColor(row.difficulty)">{{ diffText(row.difficulty) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分值" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.temp_score" :min="1" :max="50" size="small" />
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:center;margin-top:12px;">
        <el-pagination
          v-model:current-page="qPage"
          v-model:page-size="qPageSize"
          :total="qTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadQuestions"
          @current-change="loadQuestions"
        />
      </div>
      <template #footer>
        <el-button type="primary" @click="showQuestionPicker = false">确定</el-button>
      </template>
    </el-dialog>

    <!-- 排名弹窗 -->
    <el-dialog v-model="showSubmissions" :title="`${currentExam?.title || ''} - 成绩排名`" width="750px">
      <div v-if="rankingStats" style="margin-bottom:16px;">
        <el-row :gutter="12">
          <el-col :span="6"><div class="rstat"><div class="rstat-val">{{ rankingStats.participant_count }}</div><div class="rstat-lbl">参考人数</div></div></el-col>
          <el-col :span="6"><div class="rstat"><div class="rstat-val" style="color:var(--primary-color);">{{ rankingStats.avg_score }}</div><div class="rstat-lbl">平均分</div></div></el-col>
          <el-col :span="6"><div class="rstat"><div class="rstat-val" style="color:var(--success-color);">{{ rankingStats.max_score }}</div><div class="rstat-lbl">最高分</div></div></el-col>
          <el-col :span="6"><div class="rstat"><div class="rstat-val" style="color:var(--danger-color);">{{ rankingStats.min_score }}</div><div class="rstat-lbl">最低分</div></div></el-col>
        </el-row>
        <div style="margin-top:12px;">
          <div style="font-size:13px;font-weight:600;margin-bottom:6px;">📊 分数段分布</div>
          <div class="dist-row">
            <div v-for="(count, range) in rankingStats.score_distribution" :key="range" class="dist-col">
              <div class="dist-num">{{ count }}</div>
              <div class="dist-fill" :style="{height: Math.max(3, count * 10) + 'px'}"></div>
              <div class="dist-name">{{ range }}</div>
            </div>
          </div>
        </div>
      </div>
      <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
        <el-button size="small" type="success" :icon="Download" @click="exportCSV">导出CSV</el-button>
      </div>
      <el-table :data="submissions" stripe max-height="350">
        <el-table-column label="排名" width="80">
          <template #default="{ $index }">
            <el-tag v-if="$index === 0" type="warning" size="small">🥇 1</el-tag>
            <el-tag v-else-if="$index === 1" type="info" size="small">🥈 2</el-tag>
            <el-tag v-else-if="$index === 2" type="danger" size="small">🥉 3</el-tag>
            <span v-else>{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生姓名" />
        <el-table-column prop="score" label="得分" width="100" sortable />
        <el-table-column label="用时" width="100">
          <template #default="{ row }">{{ formatDuration(row.time_spent) }}</template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.submitted_at ? row.submitted_at.replace('T', ' ').slice(0, 16) : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

const exams = ref([])
const myClasses = ref([])
const questionList = ref([])
const submissions = ref([])
const rankingStats = ref(null)
const showCreate = ref(false)
const showQuestionPicker = ref(false)
const showSubmissions = ref(false)
const currentExam = ref(null)
const form = ref({ title: '', description: '', duration: 60, total_score: 100, class_ids: [], questions: [], start_time: null, end_time: null })
const qFilter = ref({ keyword: '', difficulty: '', grade: '' })
const qPage = ref(1)
const qPageSize = ref(20)
const qTotal = ref(0)

const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)
const diffColor = (d) => ({ easy: 'success', medium: 'warning', hard: 'danger' }[d] || '')

async function loadExams() {
  const res = await api.get('/exams')
  exams.value = res.items || []
}

async function loadMyClasses() {
  const res = await api.get('/teacher/my-classes')
  myClasses.value = res.items || []
}

async function loadQuestions() {
  const params = new URLSearchParams({
    page: qPage.value,
    page_size: qPageSize.value,
  })
  if (qFilter.value.keyword) params.append('keyword', qFilter.value.keyword)
  if (qFilter.value.difficulty) params.append('difficulty', qFilter.value.difficulty)
  if (qFilter.value.grade) params.append('grade', qFilter.value.grade)
  const res = await api.get(`/questions/admin?${params.toString()}`)
  questionList.value = (res.items || []).map(q => ({ ...q, temp_score: 5 }))
  qTotal.value = res.total || 0
}

function searchQuestions() {
  qPage.value = 1
  loadQuestions()
}

function openQuestionPicker() {
  showQuestionPicker.value = true
  qPage.value = 1
  loadQuestions()
}

function onQuestionSelect(rows) {
  form.value.questions = rows.map(r => ({ question_id: r.id, score: r.temp_score || 5 }))
}

async function createExam() {
  if (!form.value.title) return ElMessage.warning('请输入标题')
  if (form.value.questions.length === 0) return ElMessage.warning('请选择题目')
  const data = { ...form.value }
  if (data.start_time) data.start_time = new Date(data.start_time).toISOString()
  if (data.end_time) data.end_time = new Date(data.end_time).toISOString()
  await api.post('/exams', data)
  ElMessage.success('创建成功')
  showCreate.value = false
  form.value = { title: '', description: '', duration: 60, total_score: 100, class_ids: [], questions: [], start_time: null, end_time: null }
  loadExams()
}

async function publish(row) {
  await api.post(`/exams/${row.id}/publish`)
  ElMessage.success('发布成功')
  loadExams()
}

async function deleteItem(row) {
  await ElMessageBox.confirm(`确定删除考试「${row.title}」？`, '提示', { type: 'warning' })
  await api.delete(`/exams/${row.id}`)
  ElMessage.success('删除成功')
  loadExams()
}

async function viewRanking(row) {
  currentExam.value = row
  const res = await api.get(`/rankings/exam/${row.id}`)
  submissions.value = res.ranking || []
  rankingStats.value = {
    participant_count: res.participant_count,
    avg_score: res.avg_score,
    max_score: res.max_score,
    min_score: res.min_score,
    score_distribution: res.score_distribution,
  }
  showSubmissions.value = true
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

function exportCSV() {
  if (!currentExam.value) return
  const token = localStorage.getItem('token')
  fetch(`/api/v1/rankings/exam/${currentExam.value.id}/export`, {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentExam.value.title}_排名.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  })
}

onMounted(() => {
  loadExams()
  loadMyClasses()
  loadQuestions()
})
</script>

<style scoped>
.exam-manage { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.rstat { text-align: center; padding: 10px 0; background: var(--bg-tertiary); border-radius: 8px; }
.rstat-val { font-size: 22px; font-weight: bold; color: var(--text-primary); }
.rstat-lbl { font-size: 11px; color: var(--text-placeholder); margin-top: 2px; }
.dist-row { display: flex; align-items: flex-end; gap: 10px; height: 80px; }
.dist-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.dist-num { font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; }
.dist-fill { width: 100%; max-width: 32px; background: var(--primary-color); border-radius: 3px 3px 0 0; min-height: 3px; }
.dist-name { font-size: 10px; color: var(--text-placeholder); margin-top: 4px; }
</style>
