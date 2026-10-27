<template>
  <div class="student-exams">
    <h2>我的考试</h2>

    <el-table :data="exams" stripe v-loading="loading">
      <el-table-column prop="title" label="考试标题" />
      <el-table-column prop="duration" label="时长(分)" width="100" />
      <el-table-column prop="total_score" label="总分" width="100" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.submitted ? 'success' : 'warning'">
            {{ row.submitted ? '已完成' : '待考试' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="得分" width="100">
        <template #default="{ row }">
          <span v-if="row.submitted">{{ row.score }}分</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="startExam(row)" :disabled="row.submitted">
            {{ row.submitted ? '已完成' : '开始考试' }}
          </el-button>
          <el-button v-if="row.submitted" size="small" @click="viewRanking(row)">排名</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 考试界面 -->
    <el-dialog v-model="showExam" :title="`${currentExam?.title} - 倒计时 ${formatTime(remaining)}`" width="900px" :close-on-click-modal="false" :close-on-press-escape="false" @close="confirmClose">
      <div v-if="currentExam" class="exam-content">
        <div class="exam-info">
          <el-tag>总分：{{ currentExam.total_score }}</el-tag>
          <el-tag type="warning">时长：{{ currentExam.duration }}分钟</el-tag>
          <div class="exam-tools">
            <el-button @click="showCalc = !showCalc" circle title="计算器" size="small">🧮</el-button>
            <el-button @click="showScratch = !showScratch" circle title="草纸" size="small">📝</el-button>
          </div>
        </div>
        <div v-for="(q, idx) in currentExam.questions" :key="q.id" class="question-item">
          <div class="question-title">
            {{ idx + 1 }}. {{ q.title }}
            <el-tag size="small" type="info" style="margin-left:8px">{{ q.score }}分</el-tag>
          </div>
          <div class="question-content" v-if="q.content">{{ q.content }}</div>
          <div v-if="parseImages(q.images).length" class="question-images">
            <el-image
              v-for="(img, i) in parseImages(q.images)"
              :key="i"
              :src="img"
              :preview-src-list="parseImages(q.images)"
              :initial-index="i"
              fit="contain"
              class="question-image"
              preview-teleported
            />
          </div>
          <div v-if="q.options" class="options">
            <el-radio-group v-model="answers[q.id]">
              <el-radio v-for="opt in parsedOptions(q.options)" :key="opt.key" :label="opt.key">
                {{ opt.key }}. {{ opt.text }}
              </el-radio>
            </el-radio-group>
          </div>
          <el-input v-else v-model="answers[q.id]" placeholder="请输入答案" type="textarea" :rows="2" />
        </div>
      </div>

      <!-- 科学计算器 -->
      <div v-if="showCalc" class="calc-panel" @click.stop>
        <div class="calc-header">
          <span>🧮 科学计算器</span>
          <el-button text @click="showCalc = false">✕</el-button>
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
            <el-button text @click="showScratch = false">✕</el-button>
          </div>
        </div>
        <textarea v-model="scratchPad" class="scratch-textarea" placeholder="在这里打草稿..."></textarea>
      </div>

      <template #footer>
        <el-button type="danger" @click="submitExam">交卷</el-button>
      </template>
    </el-dialog>

    <!-- 成绩弹窗 -->
    <el-dialog v-model="showResult" title="考试成绩" width="400px">
      <div class="result-box">
        <div class="score">{{ examResult.score }}<span class="total">/{{ examResult.total }}</span></div>
        <div class="score-label">你的得分</div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showResult = false">确定</el-button>
      </template>
    </el-dialog>

    <!-- 排名弹窗 -->
    <el-dialog v-model="showRanking" title="考试排名" width="420px">
      <div v-if="rankingData" style="padding:10px 0;">
        <div style="text-align:center;margin-bottom:20px;">
          <div style="font-size:14px;color:var(--text-secondary);">{{ rankingData.exam_title }}</div>
          <div style="font-size:36px;font-weight:bold;color:var(--primary-color);margin-top:8px;">
            第 {{ rankingData.my_rank || '-' }} 名
          </div>
          <div style="font-size:13px;color:var(--text-placeholder);margin-top:4px;">
            共 {{ rankingData.participant_count }} 人参加
          </div>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="我的得分">{{ rankingData.my_score }} 分</el-descriptions-item>
          <el-descriptions-item label="班级平均">{{ rankingData.avg_score }} 分</el-descriptions-item>
          <el-descriptions-item label="我的用时">{{ formatTime(rankingData.my_time_spent || 0) }}</el-descriptions-item>
          <el-descriptions-item label="参考人数">{{ rankingData.participant_count }} 人</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:16px;">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px;color:var(--text-primary);">📊 分数段分布</div>
          <div class="dist-bar">
            <div v-for="(count, range) in rankingData.score_distribution" :key="range" class="dist-item">
              <div class="dist-count">{{ count }}</div>
              <div class="dist-bar-fill" :style="{height: Math.max(4, count * 12) + 'px'}"></div>
              <div class="dist-label">{{ range }}</div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showRanking = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const exams = ref([])
const loading = ref(false)
const showExam = ref(false)
const showResult = ref(false)
const currentExam = ref(null)
const answers = ref({})
const remaining = ref(0)
const examResult = ref({ score: 0, total: 0 })
const showRanking = ref(false)
const rankingData = ref(null)
let timer = null

// 计算器和草纸
const showCalc = ref(false)
const showScratch = ref(false)
const calcDisplay = ref('')
const scratchPad = ref('')

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
const clearScratch = () => { scratchPad.value = '' }

async function loadExams() {
  loading.value = true
  try {
    const res = await api.get('/exams')
    exams.value = res.items || []
  } finally {
    loading.value = false
  }
}

function parsedOptions(options) {
  if (typeof options === 'string') {
    try { return JSON.parse(options) } catch { return [] }
  }
  return options || []
}

function parseImages(images) {
  if (typeof images === 'string') {
    try { return JSON.parse(images) } catch { return [] }
  }
  return images || []
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

async function startExam(row) {
  await ElMessageBox.confirm(`确定开始考试「${row.title}」？开始后计时不会暂停`, '确认', { type: 'warning' })
  const res = await api.get(`/exams/${row.id}`)
  currentExam.value = res
  answers.value = {}
  remaining.value = row.duration * 60
  showExam.value = true
  await api.post(`/exams/${row.id}/start`)
  startTimer()
}

function startTimer() {
  timer = setInterval(() => {
    remaining.value--
    if (remaining.value <= 0) {
      clearInterval(timer)
      ElMessage.warning('时间到，自动交卷')
      submitExam(true)
    }
  }, 1000)
}

function confirmClose() {
  if (remaining.value > 0) {
    ElMessageBox.confirm('考试尚未结束，确定离开？', '提示', { type: 'warning' }).then(() => {
      clearInterval(timer)
      showExam.value = false
    }).catch(() => {})
  }
}

async function submitExam(auto = false) {
  if (!auto) {
    await ElMessageBox.confirm('确定交卷？交卷后不能修改', '确认', { type: 'warning' })
  }
  clearInterval(timer)
  const res = await api.post(`/exams/${currentExam.value.id}/submit`, { answers: answers.value })
  examResult.value = { score: res.score, total: currentExam.value.total_score }
  showExam.value = false
  showResult.value = true
  loadExams()
}

async function viewRanking(row) {
  try {
    const res = await api.get(`/rankings/exam/${row.id}`)
    rankingData.value = res
    showRanking.value = true
  } catch (e) {
    ElMessage.error('获取排名失败')
  }
}

onMounted(loadExams)
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.student-exams { padding: 20px; }
.student-exams h2 { margin-bottom: 20px; }
.exam-info { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }
.exam-tools { margin-left: auto; display: flex; gap: 8px; }
.question-item { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eee; }
.question-title { font-weight: 600; margin-bottom: 8px; }
.question-content { color: var(--text-secondary); margin-bottom: 12px; white-space: pre-wrap; line-height: 1.7; }
.question-images { margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 12px; }
.question-image { width: 100%; max-width: 400px; height: 200px; border-radius: 8px; border: 1px solid #eee; cursor: pointer; }
.options { padding-left: 20px; }
.result-box { text-align: center; padding: 30px 0; }
.score { font-size: 56px; font-weight: 800; color: var(--brand-600); }
.score .total { font-size: 24px; color: var(--text-placeholder); }
.score-label { color: var(--text-placeholder); margin-top: 8px; }
.dist-bar { display: flex; align-items: flex-end; gap: 8px; height: 100px; padding: 0 4px; }
.dist-item { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.dist-count { font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; }
.dist-bar-fill { width: 100%; max-width: 28px; background: var(--primary-color); border-radius: 3px 3px 0 0; min-height: 4px; }
.dist-label { font-size: 10px; color: var(--text-placeholder); margin-top: 4px; }

/* 计算器 */
.calc-panel {
  position: fixed; top: 50%; right: 20px; transform: translateY(-50%);
  width: 280px; background: #fff; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2); z-index: 3000; overflow: hidden;
}
.calc-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--brand-600); color: #fff; font-weight: 600; }
.calc-display { padding: 14px; text-align: right; font-size: 24px; font-family: monospace; background: var(--bg-tertiary); min-height: 50px; word-break: break-all; }
.calc-buttons { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; padding: 8px; }
.calc-btn { padding: 12px 0; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; transition: all 0.15s; }
.calc-btn:hover { opacity: 0.85; }
.calc-btn.num { background: #fff; border: 1px solid var(--border-strong); }
.calc-btn.op { background: var(--bg-hover); }
.calc-btn.func { background: var(--brand-50); color: var(--brand-600); }
.calc-btn.equal { background: var(--brand-600); color: #fff; }
.calc-btn.zero { grid-column: span 2; }

/* 草纸 */
.scratch-panel {
  position: fixed; top: 50%; left: 20px; transform: translateY(-50%);
  width: 300px; height: 400px; background: #fff; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2); z-index: 3000; display: flex; flex-direction: column; overflow: hidden;
}
.scratch-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--success-color); color: #fff; font-weight: 600; }
.scratch-textarea { flex: 1; border: none; padding: 12px; font-size: 14px; resize: none; outline: none; font-family: inherit; line-height: 1.6; }
</style>
