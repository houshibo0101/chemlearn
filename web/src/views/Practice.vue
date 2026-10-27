<template>
  <div class="app-container" style="padding-bottom:80px;">
    <h2 style="margin-bottom:16px;">📝 刷题</h2>

    <!-- 错题重练横幅 -->
    <el-card v-if="wrongMode" class="page-card" style="margin-bottom:16px;border-left:4px solid #F59E0B;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
        <div style="font-size:14px;">
          🔁 <b>错题重练模式</b>：已自动选入你最近的 <b style="color:var(--brand-600);">{{ total }}</b> 道错题，点击右下角开始刷题。做完后答对的题会保留在错题本，答错会重新累计。
        </div>
        <el-button size="small" @click="$router.push('/practice')">返回普通刷题</el-button>
      </div>
    </el-card>

    <!-- 筛选 -->
    <el-card v-if="!wrongMode" class="page-card">
      <el-form :inline="true" :model="filter" size="default">
        <el-form-item label="学段">
          <el-select v-model="filter.grade" clearable placeholder="全部" style="width:100px;">
            <el-option label="高一" value="高一" /><el-option label="高二" value="高二" /><el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="filter.difficulty" clearable placeholder="全部" style="width:100px;">
            <el-option label="简单" value="easy" /><el-option label="中等" value="medium" /><el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="题型">
          <el-select v-model="filter.question_type" clearable placeholder="全部" style="width:100px;">
            <el-option label="单选" value="single" /><el-option label="多选" value="multiple" /><el-option label="填空" value="fill" /><el-option label="计算" value="calculation" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-switch v-model="filter.random" active-text="随机" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="page=1; loadQuestions()" :loading="loading" :icon="Search">筛选题目</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 题目预览列表 -->
    <div v-if="questions.length > 0" style="margin-top:16px;">
      <!-- 操作栏 -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="color:var(--text-secondary);font-size:14px;">
          共 <b>{{ total }}</b> 道题，已选 <b style="color:var(--brand-600);">{{ selectedIds.length }}</b> 道
        </div>
        <div style="display:flex;gap:8px;">
          <el-button size="small" @click="selectAllPage" :disabled="questions.length === 0">全选本页</el-button>
          <el-button size="small" @click="clearSelect" :disabled="selectedIds.length === 0">清空选择</el-button>
          <el-button type="success" @click="startExam" :disabled="selectedIds.length === 0" :icon="VideoPlay">开始刷题（{{ selectedIds.length }}题）</el-button>
        </div>
      </div>

      <!-- 题目卡片 -->
      <el-card
        class="page-card question-card"
        v-for="(q, idx) in questions"
        :key="q.id"
        :class="{ selected: selectedIds.includes(q.id) }"
        @click="toggleSelect(q.id)"
        style="margin-bottom:12px;cursor:pointer;"
      >
        <div style="display:flex;gap:12px;">
          <!-- 复选框 -->
          <div style="flex-shrink:0;padding-top:2px;">
            <el-checkbox :model-value="selectedIds.includes(q.id)" @change="toggleSelect(q.id)" />
          </div>
          <!-- 题目内容 -->
          <div style="flex:1;min-width:0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <div>
                <el-tag size="small" :type="typeColor(q.question_type)">{{ typeText(q.question_type) }}</el-tag>
                <el-tag size="small" :type="diffColor(q.difficulty)" style="margin-left:6px;">{{ diffText(q.difficulty) }}</el-tag>
                <el-tag v-if="q.grade" size="small" type="info" style="margin-left:6px;">{{ q.grade }}</el-tag>
                <span v-if="q.knowledge_point" style="margin-left:8px;font-size:12px;color:var(--text-placeholder);">{{ q.knowledge_point }}</span>
              </div>
              <span style="font-size:12px;color:var(--text-disabled);">第 {{ (page - 1) * pageSize + idx + 1 }} 题</span>
            </div>
            <div style="font-size:14px;line-height:1.6;">
              <el-tag size="small" type="info" style="margin-right:6px;">{{ q.question_code || 'Q' + String(q.id).padStart(4, '0') }}</el-tag>
              {{ q.title }}
            </div>
          </div>
        </div>
      </el-card>

      <!-- 分页 -->
      <div style="display:flex;justify-content:center;margin:20px 0 80px;">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadQuestions"
          @current-change="loadQuestions"
        />
      </div>

      <!-- 底部操作栏 -->
      <div style="position:fixed;bottom:0;left:0;right:0;background:var(--bg-secondary);border-top:1px solid var(--border-color);padding:12px 24px;display:flex;justify-content:space-between;align-items:center;z-index:50;">
        <div style="color:var(--text-secondary);font-size:14px;">
          已选 <b style="color:var(--brand-600);font-size:16px;">{{ selectedIds.length }}</b> 道题
        </div>
        <div style="display:flex;gap:8px;">
          <el-button @click="clearSelect" :disabled="selectedIds.length === 0">清空选择</el-button>
          <el-button type="success" size="large" @click="startExam" :disabled="selectedIds.length === 0" :icon="VideoPlay">开始刷题</el-button>
        </div>
      </div>
    </div>

    <el-empty v-else-if="!loading" description="点击筛选题目查看可用题目，然后勾选你想做的题" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { VideoPlay, Search } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const questions = ref([])
const total = ref(0)
const loading = ref(false)
const selectedIds = ref([])
const page = ref(1)
const pageSize = ref(20)
const loadedQuestions = ref({}) // 缓存所有加载过的题目 id -> question
const wrongMode = ref(false) // 错题重练模式

const filter = reactive({ grade: '', difficulty: '', question_type: '', random: false })

const typeText = (t) => { const m = { single: '单选', multiple: '多选', fill: '填空', calculation: '计算', subjective: '主观题' }; return m[(t || '').toLowerCase()] || t }
const typeColor = (t) => { const m = { single: '', multiple: 'success', fill: 'warning', calculation: 'danger', subjective: 'info' }; return m[(t || '').toLowerCase()] || '' }
const diffText = (d) => { const m = { easy: '简单', medium: '中等', hard: '困难' }; return m[(d || '').toLowerCase()] || d }
const diffColor = (d) => { const m = { easy: 'success', medium: 'warning', hard: 'danger' }; return m[(d || '').toLowerCase()] || '' }

const loadQuestions = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filter.grade) params.grade = filter.grade
    if (filter.difficulty) params.difficulty = filter.difficulty
    if (filter.question_type) params.question_type = filter.question_type
    if (filter.random) params.random = true
    const res = await api.get('/questions', { params })
    questions.value = res.items
    total.value = res.total
    // 缓存所有加载过的题目
    res.items.forEach(q => { loadedQuestions.value[q.id] = q })
    if (res.items.length === 0) {
      ElMessage.warning('没有符合条件的题目')
    }
  } finally {
    loading.value = false
  }
}

const toggleSelect = (id) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx > -1) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(id)
  }
}

const selectAllPage = () => {
  questions.value.forEach(q => {
    if (!selectedIds.value.includes(q.id)) {
      selectedIds.value.push(q.id)
    }
  })
}

const clearSelect = () => {
  selectedIds.value = []
}

const startExam = () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选题目')
    return
  }
  // 从缓存里取所有选中的题目（跨页保留）
  const selectedQuestions = selectedIds.value
    .map(id => loadedQuestions.value[id])
    .filter(q => q)
  if (selectedQuestions.length === 0) {
    ElMessage.warning('题目数据丢失，请重新选择')
    return
  }
  sessionStorage.setItem('exam_questions', JSON.stringify(selectedQuestions))
  sessionStorage.removeItem('exam_scratch')
  router.push('/practice/exam')
}

const loadWrongForRepractice = async () => {
  loading.value = true
  wrongMode.value = true
  try {
    const res = await api.get('/wrong-questions/repractice', { params: { limit: 100 } })
    questions.value = res.items || []
    total.value = res.total || 0
    res.items.forEach(q => { loadedQuestions.value[q.id] = q })
    selectedIds.value = res.items.map(q => q.id)
    if (res.items.length === 0) {
      ElMessage.success('太棒了，错题本现在是空的！')
    }
  } catch {
    ElMessage.error('加载错题失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // /practice?source=wrong 进入错题重练模式
  if (route.query.source === 'wrong') {
    loadWrongForRepractice()
  } else {
    loadQuestions()
  }
})
</script>

<style scoped>
.question-card {
  transition: all 0.2s;
  border: 2px solid transparent;
}
.question-card:hover {
  border-color: var(--brand-300);
}
.question-card.selected {
  border-color: var(--brand-600);
  background: var(--brand-50);
}
</style>
