<template>
  <el-dialog
    :model-value="modelValue"
    title="反馈 Bug / 建议"
    width="min(680px, 92vw)"
    top="6vh"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="提交会打开 GitHub 新建 Issue 页面，内容已自动填好"
      description="登录 GitHub 后点「Submit new issue」即可；没有 GitHub 账号可以点「复制报告」发给管理员。"
      style="margin-bottom:16px;"
    />

    <el-form :model="form" label-position="top">
      <el-form-item label="类型">
        <el-radio-group v-model="form.type">
          <el-radio-button value="bug">Bug / 故障</el-radio-button>
          <el-radio-button value="feature">功能建议</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="一句话说明问题，例如：结构式插入后保存丢失" />
      </el-form-item>
      <el-form-item label="问题描述" required>
        <el-input v-model="form.description" type="textarea" :rows="4" maxlength="2000" show-word-limit placeholder="你看到了什么？期望是什么？" />
      </el-form-item>
      <el-form-item label="复现步骤（可选）">
        <el-input v-model="form.steps" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="1. 打开…&#10;2. 点击…&#10;3. 出现…" />
      </el-form-item>
      <el-form-item label="联系方式（可选）">
        <el-input v-model="form.contact" maxlength="120" placeholder="邮箱 / QQ / 微信，方便确认修复" />
      </el-form-item>
    </el-form>

    <div class="bug-env">
      <strong>自动附加的环境信息</strong>
      <div>页面：{{ pageUrl }}</div>
      <div>浏览器：{{ browserInfo }}</div>
      <div>时间：{{ nowText }}</div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button @click="copyReport">复制报告</el-button>
      <a
        class="github-submit el-button el-button--primary"
        :href="githubUrl"
        target="_blank"
        rel="noopener"
        @click="onGithubClick"
      >去 GitHub 提交</a>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const REPO = 'https://github.com/houshibo0101/chemlearn'
const form = reactive({
  type: 'bug',
  title: '',
  description: '',
  steps: '',
  contact: '',
})

const pageUrl = computed(() => (typeof window !== 'undefined' ? window.location.href : ''))
const browserInfo = computed(() => (typeof navigator !== 'undefined' ? navigator.userAgent : ''))
const nowText = computed(() => new Date().toLocaleString('zh-CN'))

const buildBody = () => {
  const kind = form.type === 'bug' ? 'Bug' : '功能建议'
  return [
    `### ${kind}描述`,
    '',
    form.description.trim(),
    '',
    '### 复现步骤',
    '',
    form.steps.trim() || '（未填写）',
    '',
    '### 环境信息',
    '',
    `- 页面：${pageUrl.value}`,
    `- 浏览器：${browserInfo.value}`,
    `- 时间：${nowText.value}`,
    form.contact.trim() ? `- 联系方式：${form.contact.trim()}` : '',
    '',
    '> 由 ChemLearn 内置反馈入口生成。',
  ].filter((line) => line !== undefined).join('\n')
}

const githubUrl = computed(() => {
  const label = form.type === 'bug' ? 'bug' : 'enhancement'
  const title = `[${form.type === 'bug' ? 'Bug' : '建议'}] ${form.title.trim() || '（请填写标题）'}`
  return `${REPO}/issues/new?labels=${encodeURIComponent(label)}` +
    `&title=${encodeURIComponent(title)}&body=${encodeURIComponent(buildBody())}`
})

const validate = () => {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return false
  }
  if (!form.description.trim()) {
    ElMessage.warning('请填写问题描述')
    return false
  }
  return true
}

const onGithubClick = (event) => {
  if (!validate()) {
    event.preventDefault()
    return
  }
  ElMessage.success('已打开 GitHub，请确认内容后点 Submit new issue')
}

const copyReport = async () => {
  if (!validate()) return
  const text = `${form.type === 'bug' ? '[Bug]' : '[建议]'} ${form.title.trim()}\n\n${buildBody()}`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('报告已复制，可以粘贴发给管理员')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}
</script>

<style scoped>
.bug-env {
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-placeholder);
  font-size: 11.5px;
  line-height: 1.7;
  word-break: break-all;
}
.bug-env strong {
  display: block;
  color: var(--text-secondary);
  margin-bottom: 2px;
}
.github-submit {
  text-decoration: none;
  margin-left: 12px;
}
</style>
