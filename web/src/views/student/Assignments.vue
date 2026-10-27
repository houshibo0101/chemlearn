<template>
  <div class="student-assignments">
    <h2>我的作业</h2>

    <el-table :data="assignments" stripe v-loading="loading">
      <el-table-column prop="title" label="作业标题" />
      <el-table-column prop="question_count" label="题目数" width="100" />
      <el-table-column prop="end_time" label="截止时间" width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.submitted ? 'success' : 'warning'">
            {{ row.submitted ? '已提交' : '待完成' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="得分" width="100">
        <template #default="{ row }">
          <span v-if="row.submitted">{{ row.score }}/{{ row.question_count }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="doAssignment(row)" :disabled="row.submitted">
            {{ row.submitted ? '已完成' : '去完成' }}
          </el-button>
          <el-button v-if="row.submitted" size="small" @click="viewResult(row)">批改</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 做作业弹窗 -->
    <el-dialog v-model="showDo" :title="currentAssignment?.title" width="900px" :close-on-click-modal="false">
      <div v-if="currentAssignment" class="assignment-content">
        <div class="assignment-tools">
          <el-button @click="showCalc = !showCalc" circle title="计算器" size="small">🧮</el-button>
          <el-button @click="showScratch = !showScratch" circle title="草纸" size="small">📝</el-button>
        </div>
        <div class="assignment-desc" v-if="currentAssignment.description">
          {{ currentAssignment.description }}
        </div>
        <div v-for="(q, idx) in currentAssignment.questions" :key="q.id" class="question-item">
          <div class="question-title">{{ idx + 1 }}. {{ q.title }}</div>
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
        <el-button @click="showDo = false">取消</el-button>
        <el-button type="primary" @click="submitAssignment">提交作业</el-button>
      </template>
    </el-dialog>

    <!-- 批改结果弹窗 -->
    <el-dialog v-model="showResult" :title="`${resultData.questions?.length ? '作业批改结果' : '加载中...'}`" width="700px">
      <div v-if="resultData.score !== undefined" style="margin-bottom:16px;text-align:center;">
        <div style="font-size:42px;font-weight:bold;color:var(--primary-color);">{{ resultData.score }}<span style="font-size:20px;color:var(--text-placeholder);">/{{ resultData.total_score }}</span></div>
        <div style="font-size:13px;color:var(--text-placeholder);">总得分 · 用时 {{ resultData.time_spent || 0 }}秒</div>
      </div>
      <div v-for="(q, idx) in resultData.questions" :key="q.id" class="result-item">
        <div class="result-qtitle">
          <span style="font-weight:600;">第 {{ idx + 1 }} 题</span>
          <el-tag size="small" :type="q.is_correct ? 'success' : 'danger'" style="margin-left:8px;">
            {{ q.is_correct ? '✓ 正确' : '✗ 错误' }} {{ q.score }}/{{ q.max_score }}分
          </el-tag>
          <el-tag v-if="q.grading?.needs_review" size="small" type="warning" style="margin-left:6px;">待老师复核</el-tag>
        </div>
        <div style="font-size:14px;margin:6px 0;color:var(--text-primary);">{{ q.title }}</div>
        <el-descriptions :column="1" size="small" border style="margin:8px 0;">
          <el-descriptions-item label="你的答案">{{ q.user_answer || '未作答' }}</el-descriptions-item>
          <el-descriptions-item label="正确答案">{{ q.correct_answer }}</el-descriptions-item>
          <el-descriptions-item v-if="q.analysis" label="解析">{{ q.analysis }}</el-descriptions-item>
        </el-descriptions>
        <!-- AI批改详情（主观题） -->
        <div v-if="q.grading && q.grading.sub_questions" class="ai-grading">
          <div style="font-size:13px;font-weight:600;color:var(--primary-color);margin-bottom:6px;">🤖 AI批改详情</div>
          <div v-for="sq in q.grading.sub_questions" :key="sq.id" class="sub-grading">
            <div style="display:flex;justify-content:space-between;font-size:13px;">
              <span style="font-weight:600;">小问 {{ sq.id }}</span>
              <span :style="{color: sq.score > 0 ? 'var(--success-color)' : 'var(--danger-color)'}">
                {{ sq.score }} 分
              </span>
            </div>
            <div v-if="sq.comment" style="font-size:12px;color:var(--text-secondary);margin-top:4px;line-height:1.6;">{{ sq.comment }}</div>
          </div>
          <div v-if="q.grading.overall_comment" style="margin-top:8px;padding:8px;background:var(--bg-tertiary);border-radius:6px;font-size:12px;color:var(--text-secondary);">
            <span style="font-weight:600;">总评：</span>{{ q.grading.overall_comment }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showResult = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const assignments = ref([])
const loading = ref(false)
const showDo = ref(false)
const showResult = ref(false)
const currentAssignment = ref(null)
const answers = ref({})
const resultData = ref({})

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

async function loadAssignments() {
  loading.value = true
  try {
    const res = await api.get('/assignments')
    assignments.value = res.items || []
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

async function doAssignment(row) {
  const res = await api.get(`/assignments/${row.id}`)
  currentAssignment.value = res
  answers.value = {}
  showDo.value = true
}

async function submitAssignment() {
  await ElMessageBox.confirm('确定提交作业？提交后不能修改', '确认', { type: 'warning' })
  const res = await api.post(`/assignments/${currentAssignment.value.id}/submit`, { answers: answers.value })
  ElMessage.success(`提交成功！得分：${res.score}/${res.total}`)
  showDo.value = false
  loadAssignments()
}

async function viewResult(row) {
  try {
    const res = await api.get(`/assignments/${row.id}/my-result`)
    resultData.value = res
    showResult.value = true
  } catch {
    ElMessage.error('获取批改结果失败')
  }
}

onMounted(loadAssignments)
</script>

<style scoped>
.student-assignments { padding: 20px; }
.student-assignments h2 { margin-bottom: 20px; }
.assignment-tools { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
.assignment-desc { padding: 12px; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 16px; }
.question-item { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eee; }
.question-title { font-weight: 600; margin-bottom: 8px; }
.question-content { color: var(--text-secondary); margin-bottom: 12px; white-space: pre-wrap; line-height: 1.7; }
.question-images { margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 12px; }
.question-image { width: 100%; max-width: 400px; height: 200px; border-radius: 8px; border: 1px solid #eee; cursor: pointer; }
.options { padding-left: 20px; }
.result-item { margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid var(--border-color); }
.result-item:last-child { border-bottom: none; }
.result-qtitle { margin-bottom: 6px; }
.ai-grading { margin-top: 8px; padding: 10px; background: var(--bg-tertiary); border-radius: 8px; border-left: 3px solid var(--primary-color); }
.sub-grading { padding: 6px 0; border-bottom: 1px dashed var(--border-color); }
.sub-grading:last-child { border-bottom: none; }

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
