<template>
  <div class="exam-container">
    <!-- 顶部栏 -->
    <div class="exam-header">
      <div class="header-left">
        <el-button :icon="Back" @click="exitExam" circle />
        <span style="margin-left:12px;font-weight:bold;font-size:16px;">化学刷题</span>
        <el-tag v-if="examSubmitted" type="success" style="margin-left:12px;">已交卷</el-tag>
      </div>
      <div class="header-center">
        <span class="timer">⏱ {{ formatTime(elapsed) }}</span>
        <span class="progress">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
        <span v-if="!examSubmitted" style="color:var(--text-placeholder);font-size:13px;">已答 {{ answeredCount }} 题</span>
      </div>
      <div class="header-right">
        <el-button @click="showCalc = !showCalc" circle title="计算器" style="font-size:18px;">🧮</el-button>
        <el-button @click="showScratch = !showScratch" circle title="草纸" style="font-size:18px;">📝</el-button>
        <el-button v-if="!examSubmitted" type="danger" @click="submitAll">交卷</el-button>
        <el-button v-else type="primary" @click="exitExam">返回选题</el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="exam-body">
      <!-- 题目区 -->
      <div class="question-area" v-if="currentQuestion">
        <div class="question-meta">
          <el-tag size="small" :type="typeColor(currentQuestion.question_type)">{{ typeText(currentQuestion.question_type) }}</el-tag>
          <el-tag size="small" :type="diffColor(currentQuestion.difficulty)" style="margin-left:6px;">{{ diffText(currentQuestion.difficulty) }}</el-tag>
          <el-tag v-if="currentQuestion.grade" size="small" type="info" style="margin-left:6px;">{{ currentQuestion.grade }}</el-tag>
          <span v-if="currentQuestion.knowledge_point" style="margin-left:8px;font-size:12px;color:var(--text-placeholder);">{{ currentQuestion.knowledge_point }}</span>
          <el-button
            text
            size="small"
            style="margin-left:auto;float:right;"
            @click="toggleFavorite(currentQuestion.id)"
          >
            <el-icon :size="18" :style="{color: favoritedIds.includes(currentQuestion.id) ? 'var(--warning-color)' : 'var(--text-placeholder)'}">
              <component :is="favoritedIds.includes(currentQuestion.id) ? 'StarFilled' : 'Star'" />
            </el-icon>
          </el-button>
        </div>

        <div class="question-title">
          <el-tag size="small" type="info" style="margin-right:8px;">{{ currentQuestion.question_code || 'Q' + String(currentQuestion.id).padStart(4, '0') }}</el-tag>
          {{ currentQuestion.title }}
        </div>
        <div v-if="currentQuestion.content" class="question-content">{{ currentQuestion.content }}</div>
        <div v-if="parseImages(currentQuestion.images).length" class="question-images">
          <img v-for="(img, i) in parseImages(currentQuestion.images)" :key="i" :src="img" class="question-image" @click="previewImage(img)" />
        </div>

        <!-- 选项（交卷前可编辑，交卷后禁用） -->
        <div v-if="currentQuestion.options" class="options-area">
          <el-radio-group v-if="currentQuestion.question_type==='single'" v-model="answers[currentQuestion.id]" size="large" :disabled="examSubmitted">
            <div v-for="opt in parseOptions(currentQuestion.options)" :key="opt.key" class="option-item">
              <el-radio :label="opt.key" border :class="{
                'option-correct': examSubmitted && isCorrectOption(currentQuestion, opt.key),
                'option-wrong': examSubmitted && isWrongOption(currentQuestion, opt.key),
              }">{{ opt.key }}. {{ opt.text }}</el-radio>
            </div>
          </el-radio-group>
          <el-checkbox-group v-else-if="currentQuestion.question_type==='multiple'" v-model="multiAnswers[currentQuestion.id]" :disabled="examSubmitted">
            <div v-for="opt in parseOptions(currentQuestion.options)" :key="opt.key" class="option-item">
              <el-checkbox :label="opt.key" border :class="{
                'option-correct': examSubmitted && isCorrectOption(currentQuestion, opt.key),
                'option-wrong': examSubmitted && isWrongOption(currentQuestion, opt.key),
              }">{{ opt.key }}. {{ opt.text }}</el-checkbox>
            </div>
          </el-checkbox-group>
        </div>

        <!-- 分小问答题（简答题/大题） -->
        <div v-else-if="parseSubQuestions(currentQuestion.sub_questions).length" class="sub-questions-area">
          <div v-for="sq in parseSubQuestions(currentQuestion.sub_questions)" :key="sq.id" class="sub-question-item">
            <div class="sub-question-content">{{ sq.content }}</div>
            <el-input
              :value="subAnswers[currentQuestion.id]?.[sq.id]"
              @input="(val) => setSubAnswer(currentQuestion.id, sq.id, val)"
              type="textarea"
              :rows="2"
              :placeholder="`第${sq.id}小问答案`"
              class="sub-answer-input"
              :disabled="examSubmitted"
            />
            <!-- 交卷后显示小问结果 -->
            <div v-if="examSubmitted && results[currentQuestion.id]?.sub_results" class="sub-question-result">
              <span :class="getSubResult(sq.id)?.is_correct ? 'sub-correct' : 'sub-wrong'">
                {{ getSubResult(sq.id)?.is_correct ? '✓' : '✗' }} 得分：{{ getSubResult(sq.id)?.score || 0 }}/{{ sq.score }}
              </span>
              <span v-if="getSubResult(sq.id)?.user_answer" class="sub-user-answer">你的答案：{{ getSubResult(sq.id).user_answer }}</span>
              <span class="sub-correct-answer">正确答案：{{ getSubResult(sq.id)?.correct_answer }}</span>
            </div>
          </div>
        </div>

        <!-- 填空/计算 -->
        <el-input v-else v-model="answers[currentQuestion.id]" type="textarea" :rows="3" placeholder="请输入你的答案" class="fill-input" :disabled="examSubmitted" />

        <!-- 交卷后显示结果 -->
        <div v-if="examSubmitted && results[currentQuestion.id]" style="margin-top:20px;">
          <el-alert :type="results[currentQuestion.id].is_correct ? 'success' : 'error'" :title="results[currentQuestion.id].is_correct ? '✅ 回答正确！' : (results[currentQuestion.id].ai_comment || '❌ 回答错误')" show-icon>
            <template #default>
              <div style="font-size:14px;line-height:1.8;">
                <template v-if="!results[currentQuestion.id].sub_results">
                  <p><strong>你的答案：</strong>{{ results[currentQuestion.id].user_answer || '未作答' }}</p>
                  <p><strong>正确答案：</strong>{{ results[currentQuestion.id].correct_answer }}</p>
                </template>
                <p v-if="results[currentQuestion.id].analysis"><strong>解析：</strong>{{ results[currentQuestion.id].analysis }}</p>
                <p v-if="results[currentQuestion.id].recorded_as_wrong" style="color:var(--warning-color);">📌 已记录到错题本</p>
              </div>
            </template>
          </el-alert>
        </div>

        <!-- 未作答提示（交卷后） -->
        <div v-if="examSubmitted && !results[currentQuestion.id]" style="margin-top:20px;">
          <el-alert type="info" title="未作答" show-icon />
        </div>
      </div>

      <!-- 题目导航 -->
      <div class="nav-area">
        <el-button @click="prevQuestion" :disabled="currentIndex === 0" :icon="ArrowLeft">上一题</el-button>
        <div class="nav-dots">
          <span
            v-for="(q, idx) in questions"
            :key="q.id"
            class="nav-dot"
            :class="{
              active: idx === currentIndex,
              answered: !examSubmitted && (answers[q.id] || multiAnswers[q.id]?.length),
              correct: examSubmitted && results[q.id]?.is_correct,
              wrong: examSubmitted && results[q.id] && !results[q.id].is_correct,
              unanswered: examSubmitted && !results[q.id],
            }"
            @click="goTo(idx)"
          >{{ idx + 1 }}</span>
        </div>
        <el-button @click="nextQuestion" :disabled="currentIndex === questions.length - 1">下一题<el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button>
      </div>
    </div>

    <!-- 科学计算器 -->
    <div v-if="showCalc" class="calc-panel" @click.stop>
      <div class="calc-header">
        <span>🧮 科学计算器</span>
        <el-button text @click="showCalc = false"><el-icon><Close /></el-icon></el-button>
      </div>
      <div class="calc-display">{{ calcDisplay || '0' }}</div>
      <div class="calc-buttons">
        <button class="calc-btn func" @click="calcInput('sin(')">sin</button>
        <button class="calc-btn func" @click="calcInput('cos(')">cos</button>
        <button class="calc-btn func" @click="calcInput('tan(')">tan</button>
        <button class="calc-btn func" @click="calcInput('log(')">log</button>
        <button class="calc-btn func" @click="calcInput('ln(')">ln</button>
        <button class="calc-btn func" @click="calcInput('sqrt(')">√</button>
        <button class="calc-btn func" @click="calcInput('**2')">x²</button>
        <button class="calc-btn func" @click="calcInput('**')">x^y</button>
        <button class="calc-btn func" @click="calcInput('Math.PI')">π</button>
        <button class="calc-btn func" @click="calcInput('Math.E')">e</button>
        <button class="calc-btn op" @click="calcInput('(')">(</button>
        <button class="calc-btn op" @click="calcInput(')')">)</button>
        <button class="calc-btn op" @click="calcClear">C</button>
        <button class="calc-btn op" @click="calcBackspace">⌫</button>
        <button class="calc-btn op" @click="calcInput('/')">÷</button>
        <button class="calc-btn num" @click="calcInput('7')">7</button>
        <button class="calc-btn num" @click="calcInput('8')">8</button>
        <button class="calc-btn num" @click="calcInput('9')">9</button>
        <button class="calc-btn op" @click="calcInput('*')">×</button>
        <button class="calc-btn num" @click="calcInput('4')">4</button>
        <button class="calc-btn num" @click="calcInput('5')">5</button>
        <button class="calc-btn num" @click="calcInput('6')">6</button>
        <button class="calc-btn op" @click="calcInput('-')">−</button>
        <button class="calc-btn num" @click="calcInput('1')">1</button>
        <button class="calc-btn num" @click="calcInput('2')">2</button>
        <button class="calc-btn num" @click="calcInput('3')">3</button>
        <button class="calc-btn op" @click="calcInput('+')">+</button>
        <button class="calc-btn num zero" @click="calcInput('0')">0</button>
        <button class="calc-btn num" @click="calcInput('.')">.</button>
        <button class="calc-btn equal" @click="calcEqual">=</button>
      </div>
    </div>

    <!-- 草纸 -->
    <div v-if="showScratch" class="scratch-panel">
      <div class="scratch-header">
        <span>📝 草纸</span>
        <div>
          <el-button text size="small" @click="clearScratch">清空</el-button>
          <el-button text @click="showScratch = false"><el-icon><Close /></el-icon></el-button>
        </div>
      </div>
      <textarea
        v-model="scratchPad"
        class="scratch-textarea"
        placeholder="在这里打草稿..."
        @input="saveScratch"
        :disabled="examSubmitted"
      ></textarea>
    </div>

    <!-- 交卷确认弹窗 -->
    <el-dialog v-model="showConfirm" title="确认交卷" width="400px">
      <p>共 {{ questions.length }} 道题，已答 {{ answeredCount }} 道，未答 {{ questions.length - answeredCount }} 道。</p>
      <p style="color:var(--warning-color);">交卷后将自动判分，无法再修改答案。</p>
      <template #footer>
        <el-button @click="showConfirm = false">再检查一下</el-button>
        <el-button type="danger" :loading="submitting" @click="doSubmit">确认交卷</el-button>
      </template>
    </el-dialog>

    <!-- 交卷结果弹窗 -->
    <el-dialog v-model="showResult" title="📊 答题结果" width="500px" :close-on-click-modal="false">
      <div style="text-align:center;padding:20px 0;">
        <div style="font-size:48px;margin-bottom:12px;">{{ score >= 60 ? '🎉' : '💪' }}</div>
        <div style="font-size:32px;font-weight:bold;color:var(--brand-600);">{{ score }} 分</div>
        <div style="color:var(--text-placeholder);margin-top:8px;">
          正确 {{ correctCount }} 题 / 共 {{ questions.length }} 题 · 用时 {{ formatTime(elapsed) }}
        </div>
      </div>
      <el-descriptions :column="2" border size="small" style="margin-top:16px;">
        <el-descriptions-item label="总题数">{{ questions.length }}</el-descriptions-item>
        <el-descriptions-item label="已作答">{{ answeredCount }}</el-descriptions-item>
        <el-descriptions-item label="正确">{{ correctCount }}</el-descriptions-item>
        <el-descriptions-item label="错误">{{ wrongCount }}</el-descriptions-item>
        <el-descriptions-item label="未答">{{ questions.length - answeredCount }}</el-descriptions-item>
        <el-descriptions-item label="正确率">{{ accuracy }}%</el-descriptions-item>
        <el-descriptions-item label="用时">{{ formatTime(elapsed) }}</el-descriptions-item>
        <el-descriptions-item label="得分">{{ score }}分</el-descriptions-item>
      </el-descriptions>
      <p style="margin-top:16px;font-size:13px;color:var(--text-placeholder);">💡 关闭弹窗后可查看每道题的对错和解析，错题已自动记录到错题本。</p>
      <template #footer>
        <el-button @click="showResult = false">查看错题</el-button>
        <el-button type="primary" @click="exitExam">返回选题</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Close, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const questions = ref([])
const currentIndex = ref(0)
const answers = reactive({})
const multiAnswers = reactive({})
const subAnswers = reactive({})
const results = reactive({})
const submitting = ref(false)
const showCalc = ref(false)
const showScratch = ref(false)
const showConfirm = ref(false)
const showResult = ref(false)
const examSubmitted = ref(false)
const favoritedIds = ref([])

// 计时器
const elapsed = ref(0)
let timer = null

// 计算器
const calcDisplay = ref('')

// 草纸
const scratchPad = ref('')

const currentQuestion = computed(() => questions.value[currentIndex.value])

const parseOptions = (s) => { try { return JSON.parse(s) } catch { return [] } }
const parseImages = (s) => { try { return s ? JSON.parse(s) : [] } catch { return [] } }
const parseSubQuestions = (s) => { try { return s ? JSON.parse(s) : [] } catch { return [] } }
const setSubAnswer = (qId, sqId, val) => {
  if (!subAnswers[qId]) subAnswers[qId] = {}
  subAnswers[qId][sqId] = val
}
const getSubResult = (sqId) => {
  const r = results[currentQuestion.value?.id]
  if (!r?.sub_results) return null
  return r.sub_results.find(sr => String(sr.id) === String(sqId))
}
const previewImage = (src) => {
  window.open(src, '_blank')
}

const loadFavorites = async () => {
  try {
    const res = await api.get('/favorites/question-ids')
    favoritedIds.value = res.ids || []
  } catch {}
}

const toggleFavorite = async (qid) => {
  try {
    if (favoritedIds.value.includes(qid)) {
      await api.delete(`/favorites/${qid}`)
      favoritedIds.value = favoritedIds.value.filter(id => id !== qid)
      ElMessage.success('已取消收藏')
    } else {
      await api.post(`/favorites/${qid}`)
      favoritedIds.value.push(qid)
      ElMessage.success('收藏成功')
    }
  } catch {}
}
const typeText = (t) => ({ single: '单选', multiple: '多选', fill: '填空', calculation: '计算' }[t] || t)
const typeColor = (t) => ({ single: '', multiple: 'success', fill: 'warning', calculation: 'danger' }[t] || '')
const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)
const diffColor = (d) => ({ easy: 'success', medium: 'warning', hard: 'danger' }[d] || '')

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

// 统计
const answeredCount = computed(() => questions.value.filter(q => answers[q.id] || (multiAnswers[q.id] && multiAnswers[q.id].length)).length)
const correctCount = computed(() => questions.value.filter(q => results[q.id]?.is_correct).length)
const wrongCount = computed(() => questions.value.filter(q => results[q.id] && !results[q.id].is_correct).length)
const accuracy = computed(() => answeredCount.value > 0 ? Math.round(correctCount.value / answeredCount.value * 100) : 0)
const score = computed(() => questions.value.length > 0 ? Math.round(correctCount.value / questions.value.length * 100) : 0)

// 判断选项是否正确（交卷后高亮）
const isCorrectOption = (q, key) => {
  return q.answer && q.answer.includes(key)
}
const isWrongOption = (q, key) => {
  const userAns = q.question_type === 'multiple' ? (multiAnswers[q.id] || []) : [answers[q.id]]
  return userAns.includes(key) && !q.answer?.includes(key)
}

// 计时器
const startTimer = () => {
  timer = setInterval(() => { elapsed.value++ }, 1000)
}
onUnmounted(() => { if (timer) clearInterval(timer) })

// 导航
const prevQuestion = () => { if (currentIndex.value > 0) currentIndex.value-- }
const nextQuestion = () => { if (currentIndex.value < questions.value.length - 1) currentIndex.value++ }
const goTo = (idx) => { currentIndex.value = idx }

// 交卷
const submitAll = () => {
  showConfirm.value = true
}

const doSubmit = async () => {
  submitting.value = true
  showConfirm.value = false
  if (timer) clearInterval(timer)

  // 逐题提交判分
  for (const q of questions.value) {
    let userAnswer = answers[q.id] || ''
    if (q.question_type === 'multiple') {
      userAnswer = (multiAnswers[q.id] || []).sort().join(',')
    }
    // 分小问题目：组装JSON答案
    const subQs = parseSubQuestions(q.sub_questions)
    if (subQs.length) {
      const subAns = {}
      let hasAnswer = false
      for (const sq of subQs) {
        const val = subAnswers[q.id]?.[sq.id] || ''
        subAns[sq.id] = val
        if (val.trim()) hasAnswer = true
      }
      userAnswer = hasAnswer ? JSON.stringify(subAns) : ''
    }
    if (userAnswer) {
      try {
        const res = await api.post('/questions/answer', { question_id: q.id, user_answer: userAnswer })
        results[q.id] = res
      } catch (e) {
        // 单题失败不影响其他题
      }
    }
  }

  examSubmitted.value = true
  submitting.value = false
  showResult.value = true
  ElMessage.success('交卷成功，已自动判分')
}

// 退出
const exitExam = () => {
  sessionStorage.removeItem('exam_questions')
  sessionStorage.removeItem('exam_scratch')
  router.push('/practice')
}

// 计算器
const calcInput = (val) => { calcDisplay.value += val }
const calcClear = () => { calcDisplay.value = '' }
const calcBackspace = () => { calcDisplay.value = calcDisplay.value.slice(0, -1) }
const calcEqual = () => {
  try {
    let expr = calcDisplay.value
      .replace(/sin\(/g, 'Math.sin(')
      .replace(/cos\(/g, 'Math.cos(')
      .replace(/tan\(/g, 'Math.tan(')
      .replace(/log\(/g, 'Math.log10(')
      .replace(/ln\(/g, 'Math.log(')
      .replace(/sqrt\(/g, 'Math.sqrt(')
    const result = Function('"use strict"; return (' + expr + ')')()
    calcDisplay.value = String(Number(result.toFixed(10)))
  } catch {
    ElMessage.error('表达式错误')
  }
}

// 草纸
const saveScratch = () => { sessionStorage.setItem('exam_scratch', scratchPad.value) }
const clearScratch = () => {
  scratchPad.value = ''
  sessionStorage.removeItem('exam_scratch')
}

onMounted(() => {
  const saved = sessionStorage.getItem('exam_questions')
  if (saved) {
    questions.value = JSON.parse(saved)
  }
  // 支持从收藏页面批量练习
  const favIds = sessionStorage.getItem('practice_favorites')
  if (favIds && questions.value.length === 0) {
    const ids = JSON.parse(favIds)
    api.post('/questions/batch', { ids }).then(res => {
      questions.value = res.questions || res.items || []
      sessionStorage.setItem('exam_questions', JSON.stringify(questions.value))
    }).catch(() => {})
    sessionStorage.removeItem('practice_favorites')
  }
  if (questions.value.length === 0) {
    ElMessage.warning('请先选择题目')
    router.push('/practice')
    return
  }
  const savedScratch = sessionStorage.getItem('exam_scratch')
  if (savedScratch) scratchPad.value = savedScratch
  startTimer()
  loadFavorites()
})
</script>

<style scoped>
.exam-container {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
}
.exam-header {
  background: color-mix(in srgb, var(--bg-secondary) 90%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-center {
  display: flex;
  align-items: center;
  gap: 24px;
}
.timer {
  font-size: 19px;
  font-weight: 800;
  color: var(--brand-600);
  font-family: var(--font-mono);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.progress {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 600;
}
.exam-body {
  flex: 1;
  max-width: 920px;
  margin: 0 auto;
  padding: 22px 20px 40px;
  width: 100%;
}
.question-area {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 26px;
  min-height: 400px;
  box-shadow: var(--shadow-sm);
}
.question-meta {
  margin-bottom: 16px;
}
.question-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.7;
  margin-bottom: 12px;
  letter-spacing: -0.01em;
}
.question-content {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  white-space: pre-wrap;
  line-height: 1.8;
}
.question-images {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.question-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: var(--radius-md);
  cursor: pointer;
  border: 1px solid var(--border-color);
  object-fit: contain;
  transition: box-shadow var(--dur) var(--ease);
}
.question-image:hover {
  box-shadow: var(--shadow-lg);
}
.sub-questions-area {
  margin-bottom: 16px;
}
.sub-question-item {
  margin-bottom: 20px;
  padding: 14px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}
.sub-question-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.7;
  margin-bottom: 10px;
}
.sub-answer-input {
  margin-bottom: 8px;
}
.sub-question-result {
  font-size: 13px;
  line-height: 1.8;
  padding-top: 8px;
  border-top: 1px dashed var(--border-strong);
}
.sub-correct { color: var(--success-color); font-weight: 600; margin-right: 12px; }
.sub-wrong { color: var(--danger-color); font-weight: 600; margin-right: 12px; }
.sub-user-answer { color: var(--text-placeholder); margin-right: 12px; }
.sub-correct-answer { color: var(--success-color); }
.options-area {
  margin-top: 16px;
}
.option-item {
  margin-bottom: 10px;
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--dur) var(--ease);
}
.option-item:hover { border-color: var(--brand-300); background: var(--brand-50); }
.option-item :deep(.el-radio), .option-item :deep(.el-checkbox) {
  width: 100%;
  height: auto;
}
.option-item :deep(.el-radio__label), .option-item :deep(.el-checkbox__label) {
  white-space: normal;
  line-height: 1.7;
}
.option-correct { border-color: var(--success-color); background: var(--success-light); }
.option-correct :deep(.el-radio__label), .option-correct :deep(.el-checkbox__label) {
  color: var(--success-deep);
  font-weight: 600;
}
.option-wrong { border-color: var(--danger-color); background: var(--danger-light); }
.option-wrong :deep(.el-radio__label), .option-wrong :deep(.el-checkbox__label) {
  color: var(--danger-deep);
  text-decoration: line-through;
}
.fill-input {
  margin-top: 16px;
}
.nav-area {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 22px;
  gap: 16px;
}
.nav-dots {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  justify-content: center;
  flex: 1;
}
.nav-dot {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  border: 1px solid var(--border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--dur) var(--ease);
  color: var(--text-secondary);
}
.nav-dot:hover { border-color: var(--brand-500); color: var(--brand-600); transform: translateY(-2px); }
.nav-dot.active {
  background: var(--gradient-brand);
  color: #fff;
  border-color: transparent;
  box-shadow: var(--shadow-brand-sm);
}
.nav-dot.answered { border-color: var(--success-color); }
.nav-dot.correct { background: var(--success-light); border-color: var(--success-color); color: var(--success-deep); }
.nav-dot.wrong { background: var(--danger-light); border-color: var(--danger-color); color: var(--danger-deep); }
.nav-dot.unanswered { background: var(--bg-tertiary); border-color: var(--border-color); color: var(--text-placeholder); }

/* 计算器 */
.calc-panel {
  position: fixed;
  right: 20px;
  top: 80px;
  width: 280px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  overflow: hidden;
}
.calc-header {
  background: var(--gradient-brand);
  color: #fff;
  padding: 11px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}
.calc-display {
  padding: 16px;
  font-size: 24px;
  text-align: right;
  font-family: var(--font-mono);
  background: var(--bg-tertiary);
  min-height: 40px;
  word-break: break-all;
  font-variant-numeric: tabular-nums;
}
.calc-buttons {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 5px;
  padding: 9px;
}
.calc-btn {
  padding: 12px 0;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s var(--ease);
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.calc-btn:hover { background: var(--border-color); }
.calc-btn.num { background: var(--bg-secondary); border: 1px solid var(--border-strong); }
.calc-btn.func { background: var(--brand-50); color: var(--brand-600); }
.calc-btn.op { background: var(--warning-light); color: var(--warning-deep); }
.calc-btn.equal { background: var(--success-color); color: #fff; }
.calc-btn.zero { grid-column: span 2; }

/* 草纸 */
.scratch-panel {
  position: fixed;
  right: 20px;
  top: 80px;
  width: 320px;
  height: 480px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.scratch-header {
  background: var(--gradient-emerald);
  color: #fff;
  padding: 11px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}
.scratch-textarea {
  flex: 1;
  border: none;
  padding: 16px;
  font-size: 14px;
  line-height: 1.8;
  resize: none;
  outline: none;
  font-family: var(--font-mono);
  background: var(--bg-secondary);
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .calc-panel, .scratch-panel {
    right: 10px;
    left: 10px;
    width: auto;
    top: 70px;
  }
  .header-center { gap: 12px; }
  .timer { font-size: 16px; }
  .question-area { padding: 16px; }
  .exam-body { padding: 14px 12px 32px; }
  .option-item { padding: 10px 12px; }
}
</style>
