<template>
  <div class="assignment-manage">
    <div class="page-header">
      <h2>作业管理</h2>
      <el-button type="primary" @click="showCreate = true">+ 布置作业</el-button>
    </div>

    <el-table :data="assignments" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="作业标题" />
      <el-table-column prop="question_count" label="题目数" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'info'">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="end_time" label="截止时间" width="180" />
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="viewSubmissions(row)" v-if="row.status === 'published'">提交情况</el-button>
          <el-button size="small" type="success" @click="publish(row)" v-if="row.status === 'draft'">发布</el-button>
          <el-button size="small" type="danger" @click="deleteItem(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建作业弹窗 -->
    <el-dialog v-model="showCreate" title="布置作业" width="700px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="作业标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="作业说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="选择班级">
          <el-select v-model="form.class_ids" multiple placeholder="选择发布班级" style="width:100%">
            <el-option v-for="c in myClasses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择题目">
          <div class="question-picker">
            <el-button @click="openQuestionPicker">已选 {{ form.question_ids.length }} 题</el-button>
          </div>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择截止时间" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createAssignment">创建</el-button>
      </template>
    </el-dialog>

    <!-- 题目选择弹窗 -->
    <el-dialog v-model="showQuestionPicker" title="选择题目" width="900px">
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
        <span style="margin-left:auto;line-height:32px;color:var(--text-placeholder);font-size:13px;">共 {{ qTotal }} 题，已选 {{ form.question_ids.length }} 题</span>
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
        <el-table-column prop="grade" label="学段" width="80" />
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
        <el-button type="primary" @click="showQuestionPicker = false">确定（已选 {{ form.question_ids.length }} 题）</el-button>
      </template>
    </el-dialog>

    <!-- 提交情况弹窗 -->
    <el-dialog v-model="showSubmissions" :title="`${currentAssignment?.title || ''} - 提交情况`" width="600px">
      <el-table :data="submissions" stripe>
        <el-table-column prop="student_name" label="学生" />
        <el-table-column prop="score" label="得分" width="100" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="submitted_at" label="提交时间" width="180" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const assignments = ref([])
const myClasses = ref([])
const questionList = ref([])
const submissions = ref([])
const showCreate = ref(false)
const showQuestionPicker = ref(false)
const showSubmissions = ref(false)
const currentAssignment = ref(null)
const form = ref({ title: '', description: '', class_ids: [], question_ids: [], end_time: null })
const qFilter = ref({ keyword: '', difficulty: '', grade: '' })
const qPage = ref(1)
const qPageSize = ref(20)
const qTotal = ref(0)

const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)
const diffColor = (d) => ({ easy: 'success', medium: 'warning', hard: 'danger' }[d] || '')

async function loadAssignments() {
  const res = await api.get('/assignments')
  assignments.value = res.items || []
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
  questionList.value = res.items || []
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
  form.value.question_ids = rows.map(r => r.id)
}

async function createAssignment() {
  if (!form.value.title) return ElMessage.warning('请输入标题')
  if (form.value.question_ids.length === 0) return ElMessage.warning('请选择题目')
  const data = { ...form.value }
  if (data.end_time) data.end_time = new Date(data.end_time).toISOString()
  await api.post('/assignments', data)
  ElMessage.success('创建成功')
  showCreate.value = false
  form.value = { title: '', description: '', class_ids: [], question_ids: [], end_time: null }
  loadAssignments()
}

async function publish(row) {
  await api.post(`/assignments/${row.id}/publish`)
  ElMessage.success('发布成功')
  loadAssignments()
}

async function deleteItem(row) {
  await ElMessageBox.confirm(`确定删除作业「${row.title}」？`, '提示', { type: 'warning' })
  await api.delete(`/assignments/${row.id}`)
  ElMessage.success('删除成功')
  loadAssignments()
}

async function viewSubmissions(row) {
  currentAssignment.value = row
  const res = await api.get(`/assignments/${row.id}/submissions`)
  submissions.value = res.items || []
  showSubmissions.value = true
}

onMounted(() => {
  loadAssignments()
  loadMyClasses()
  loadQuestions()
})
</script>

<style scoped>
.assignment-manage { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.question-picker { width: 100%; }
</style>
