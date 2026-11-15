<template>
  <el-dialog
    :model-value="modelValue"
    :title="`题目校对 · 第 ${form.no} 题`"
    width="min(760px, 94vw)"
    top="4vh"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-form :model="form" label-width="88px">
      <el-form-item label="题型">
        <el-select v-model="form.type" style="width:180px" @change="onTypeChange">
          <el-option label="单选" value="single" />
          <el-option label="多选" value="multiple" />
          <el-option label="填空" value="fill" />
          <el-option label="计算" value="calculation" />
          <el-option label="简答" value="subjective" />
        </el-select>
      </el-form-item>
      <el-form-item label="题干" required>
        <el-input v-model="form.title" type="textarea" :rows="3" maxlength="2000" show-word-limit />
      </el-form-item>
      <el-form-item label="补充材料">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="2"
          maxlength="2000"
          show-word-limit
          placeholder="图表说明、材料等，可空"
        />
      </el-form-item>
      <el-form-item v-if="isChoice" label="选项">
        <div class="option-list">
          <div v-for="(opt, i) in form.options" :key="i" class="option-row">
            <el-input v-model="opt.key" class="option-key" maxlength="2" placeholder="A" />
            <el-input v-model="opt.text" placeholder="选项内容" />
            <el-button link type="danger" @click="removeOption(i)">删除</el-button>
          </div>
          <el-button size="small" plain @click="addOption">+ 添加选项</el-button>
        </div>
      </el-form-item>
      <el-form-item v-if="!isChoice" label="小问">
        <div class="sub-editor">
          <div v-for="(sub, i) in form.sub_questions" :key="i" class="sub-row">
            <div class="sub-row__head">
              <span>第 {{ i + 1 }} 小问</span>
              <el-button link type="danger" size="small" @click="removeSub(i)">删除</el-button>
            </div>
            <el-input v-model="sub.content" type="textarea" :rows="2" placeholder="小问内容，例如 (1) 写出…" />
            <div class="sub-row__bottom">
              <el-input v-model="sub.answer" placeholder="该小问参考答案" />
              <el-input-number v-model="sub.score" :min="0" :max="100" size="small" />
            </div>
          </div>
          <div class="sub-actions">
            <el-button size="small" plain @click="addSub">+ 添加小问</el-button>
            <span v-if="form.sub_questions.length" class="sub-total">小问合计 {{ subTotal }} 分</span>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="标准答案">
        <el-input v-model="form.answer" type="textarea" :rows="2" placeholder="选择题填字母，如 A / AB；填空写参考答案" />
      </el-form-item>
      <el-form-item label="解析">
        <el-input v-model="form.analysis" type="textarea" :rows="3" placeholder="可空" />
      </el-form-item>
      <div class="two-col">
        <el-form-item label="分值">
          <el-input-number v-model="form.score" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="form.knowledge_point" placeholder="可空" />
        </el-form-item>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存并生效</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  paperId: { type: [Number, String], default: null },
  question: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])
const saving = ref(false)
const isChoice = computed(() => form.type === 'single' || form.type === 'multiple')
const subTotal = computed(() =>
  form.sub_questions.reduce((sum, sub) => sum + Number(sub.score || 0), 0))

const form = reactive({
  no: 0,
  type: 'single',
  title: '',
  content: '',
  options: [],
  sub_questions: [],
  answer: '',
  analysis: '',
  score: 5,
  knowledge_point: '',
})

const defaultOptions = () => ([
  { key: 'A', text: '' },
  { key: 'B', text: '' },
  { key: 'C', text: '' },
  { key: 'D', text: '' },
])

const loadFromQuestion = () => {
  const q = props.question || {}
  const opts = Array.isArray(q.options) ? q.options : []
  form.no = q.no || 0
  form.type = q.type || 'single'
  form.title = q.title || ''
  form.content = q.content || ''
  form.options = opts.length
    ? opts.map((o) => ({ key: String(o.key || ''), text: String(o.text || '') }))
    : defaultOptions()
  const subs = Array.isArray(q.sub_questions) ? q.sub_questions : []
  form.sub_questions = subs.map((s) => ({
    content: String(s.content || ''),
    answer: String(s.answer || ''),
    score: Number(s.score || 0),
  }))
  form.answer = q.answer || ''
  form.analysis = q.analysis || ''
  form.score = q.score || 0
  form.knowledge_point = q.knowledge_point || ''
}

const onTypeChange = () => {
  if ((form.type === 'single' || form.type === 'multiple') && !form.options.length) {
    form.options = defaultOptions()
  }
}
const addOption = () => {
  const nextKey = String.fromCharCode(65 + form.options.length)
  form.options.push({ key: nextKey, text: '' })
}
const removeOption = (index) => {
  form.options.splice(index, 1)
}
const addSub = () => {
  form.sub_questions.push({ content: '', answer: '', score: 2 })
}
const removeSub = (index) => {
  form.sub_questions.splice(index, 1)
}

const save = async () => {
  if (!form.title.trim()) {
    ElMessage.warning('题干不能为空')
    return
  }
  if (!props.paperId || !form.no) return
  saving.value = true
  try {
    const subs = isChoice.value
      ? []
      : form.sub_questions
        .filter((s) => String(s.content || '').trim() || String(s.answer || '').trim())
        .map((s) => ({
          content: String(s.content || '').trim(),
          answer: String(s.answer || '').trim(),
          score: Number(s.score || 0),
        }))
    const res = await api.patch(`/papers/${props.paperId}/questions/${form.no}`, {
      type: form.type,
      title: form.title.trim(),
      content: form.content,
      options: form.options,
      sub_questions: subs,
      answer: form.answer,
      analysis: form.analysis,
      score: subs.length ? subs.reduce((sum, s) => sum + s.score, 0) : form.score,
      knowledge_point: form.knowledge_point,
    })
    ElMessage.success(`第 ${form.no} 题已保存，做题页已更新`)
    emit('saved', res.question)
    emit('update:modelValue', false)
  } catch {
    // 错误由拦截器提示
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (visible) loadFromQuestion()
})
</script>

<style scoped>
.option-list { width: 100%; display: flex; flex-direction: column; gap: 6px; }
.option-row { display: flex; align-items: center; gap: 6px; }
.option-key { width: 54px; flex: none; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.sub-editor { width: 100%; display: flex; flex-direction: column; gap: 10px; }
.sub-row {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-tertiary);
}
.sub-row__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}
.sub-row__bottom {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.sub-row__bottom .el-input { flex: 1; }
.sub-actions { display: flex; align-items: center; gap: 12px; }
.sub-total { color: var(--text-placeholder); font-size: 12px; }
</style>
