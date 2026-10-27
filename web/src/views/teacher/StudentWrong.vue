<template>
  <div class="student-wrong">
    <div class="page-header">
      <h2>学生错题查看</h2>
      <div class="filters">
        <el-select v-model="selectedClass" placeholder="选择班级" @change="loadClassStudents" style="width:200px;margin-right:12px">
          <el-option v-for="c in myClasses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="selectedStudent" placeholder="选择学生" @change="loadWrongQuestions" style="width:200px">
          <el-option v-for="s in classStudents" :key="s.id" :label="s.full_name || s.username" :value="s.id" />
        </el-select>
      </div>
    </div>

    <div v-if="wrongQuestions.length > 0" class="stats-bar">
      <el-tag>错题总数：{{ wrongQuestions.length }}</el-tag>
      <el-tag type="warning">高频错题（错3次以上）：{{ highFrequencyCount }}</el-tag>
    </div>

    <el-table :data="wrongQuestions" stripe v-loading="loading">
      <el-table-column prop="question_code" label="题目编号" width="120" />
      <el-table-column prop="title" label="题目" show-overflow-tooltip />
      <el-table-column prop="wrong_count" label="错误次数" width="120">
        <template #default="{ row }">
          <el-tag :type="row.wrong_count >= 3 ? 'danger' : row.wrong_count >= 2 ? 'warning' : 'info'">
            {{ row.wrong_count }} 次
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_wrong_at" label="最后错误时间" width="200" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="aiExplain(row)">AI讲解</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && wrongQuestions.length === 0" description="该学生暂无错题" />

    <!-- AI讲解弹窗 -->
    <el-dialog v-model="showAI" title="AI 错题讲解" width="700px">
      <div class="ai-question">
        <strong>题目：</strong>{{ currentQuestion?.title }}
      </div>
      <div class="ai-answer" v-if="aiAnswer">
        <div v-html="renderMarkdown(aiAnswer)"></div>
      </div>
      <div v-else class="ai-loading">
        <el-icon class="is-loading"><Loading /></el-icon> AI 正在分析...
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { renderMarkdown } from '@/utils/markdown'
import { Loading } from '@element-plus/icons-vue'

const route = useRoute()
const myClasses = ref([])
const classStudents = ref([])
const wrongQuestions = ref([])
const selectedClass = ref(null)
const selectedStudent = ref(null)
const loading = ref(false)
const showAI = ref(false)
const aiAnswer = ref('')
const currentQuestion = ref(null)

const highFrequencyCount = computed(() => wrongQuestions.value.filter(w => w.wrong_count >= 3).length)

async function loadMyClasses() {
  const res = await api.get('/teacher/my-classes')
  myClasses.value = res.items || []
  if (route.query.class_id) {
    selectedClass.value = Number(route.query.class_id)
    await loadClassStudents()
    if (route.query.student_id) {
      selectedStudent.value = Number(route.query.student_id)
      await loadWrongQuestions()
    }
  }
}

async function loadClassStudents() {
  if (!selectedClass.value) return
  const res = await api.get(`/classes/${selectedClass.value}/students`)
  classStudents.value = res.items || []
}

async function loadWrongQuestions() {
  if (!selectedClass.value || !selectedStudent.value) return
  loading.value = true
  try {
    const res = await api.get(`/teacher/classes/${selectedClass.value}/wrong-questions?student_id=${selectedStudent.value}`)
    const studentData = res.items?.[0]
    wrongQuestions.value = studentData?.wrong_questions || []
  } finally {
    loading.value = false
  }
}

async function aiExplain(row) {
  currentQuestion.value = row
  showAI.value = true
  aiAnswer.value = ''
  try {
    const res = await api.post('/wrong-questions/ai-explain', {
      question_id: row.question_id,
      message: `请详细讲解这道化学题：${row.title}`,
    })
    aiAnswer.value = res.answer || res.message || '暂无讲解'
  } catch (e) {
    aiAnswer.value = 'AI 讲解失败，请稍后重试'
  }
}

onMounted(loadMyClasses)
</script>

<style scoped>
.student-wrong { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-header h2 { margin: 0; }
.filters { display: flex; }
.stats-bar { margin-bottom: 16px; display: flex; gap: 12px; }
.ai-question { padding: 12px; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 16px; }
.ai-answer { padding: 16px; background: var(--accent-100); border-radius: 8px; line-height: 1.8; }
.ai-loading { text-align: center; padding: 40px; color: var(--text-placeholder); }
</style>
