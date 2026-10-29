<template>
  <div class="app-container">
    <div class="page-head">
      <div>
        <div class="page-head__title">套卷练习</div>
        <div class="page-head__desc">
          整份高考卷限时演练，交卷后错题自动进错题本
        </div>
      </div>
      <div class="page-head__actions">
        <el-button type="primary" :icon="Upload" @click="openUpload">上传试卷</el-button>
      </div>
    </div>

    <!-- 管理员：审核筛选 -->
    <div v-if="isAdmin" class="paper-tabs">
      <button
        v-for="t in tabs"
        :key="t.value"
        class="paper-tabs__btn"
        :class="{ on: tab === t.value }"
        @click="setTab(t.value)"
      >
        {{ t.label }}
        <span v-if="t.value === 'pending' && pendingCount" class="paper-tabs__badge">{{ pendingCount }}</span>
      </button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && !list.length" description="还没有套卷，点右上角上传一份高考卷试试" />

      <div v-for="p in list" :key="p.id" class="paper-card">
        <div class="paper-card__main">
          <div class="paper-card__head">
            <div class="paper-card__title">{{ p.title }}</div>
            <el-tag :type="statusType(p)" size="small" effect="plain">{{ statusText(p) }}</el-tag>
            <el-tag v-if="p.my_best_score != null" type="success" size="small" effect="plain">
              我的最高 {{ p.my_best_score }} 分
            </el-tag>
          </div>

          <div class="paper-card__meta">
            <span v-if="p.province">{{ p.province }}</span>
            <span v-if="p.year">{{ p.year }} 年</span>
            <span v-if="p.exam_type">{{ p.exam_type }}</span>
            <span v-if="p.question_count">{{ p.question_count }} 题</span>
            <span v-if="p.total_score">总分 {{ p.total_score }}</span>
            <span v-if="p.duration">建议 {{ p.duration }} 分钟</span>
            <span v-if="p.attempt_count">{{ p.attempt_count }} 人做过</span>
          </div>

          <div v-if="p.gen_status === 'failed'" class="paper-card__err">
            生成失败：{{ p.gen_error }}
          </div>
          <div v-else-if="p.status === 'rejected'" class="paper-card__err">
            已驳回：{{ p.review_note || '内容不符合要求' }}
          </div>

          <!-- 生成进度：步骤文字 + 进度条 + 最近几条日志 -->
          <div v-else-if="p.gen_status === 'running' || p.gen_status === 'waiting'" class="gen-box">
            <div class="gen-box__row">
              <span class="gen-box__txt">{{ p.progress_text || '排队中…' }}</span>
              <span class="gen-box__pct">{{ p.progress || 0 }}%</span>
            </div>
            <el-progress
              :percentage="p.progress || 0"
              :stroke-width="5"
              :show-text="false"
              :color="progressColor"
            />
            <div v-if="p.gen_logs && p.gen_logs.length" class="gen-logs">
              <div v-for="(l, i) in p.gen_logs.slice(-3)" :key="i" class="gen-logs__item">
                <span class="gen-logs__t">{{ l.t }}</span>{{ l.m }}
              </div>
            </div>
          </div>
        </div>

        <div class="paper-card__actions">
          <!-- 学生：开始做题 -->
          <el-button
            v-if="p.ready"
            type="primary"
            size="small"
            :icon="VideoPlay"
            @click="startPaper(p)"
          >开始做题</el-button>

          <el-button
            v-else-if="p.status === 'pending'"
            size="small"
            disabled
          >等待审核</el-button>

          <el-button
            v-else-if="p.gen_status === 'running' || p.gen_status === 'waiting'"
            size="small"
            loading
          >生成中</el-button>

          <!-- 管理员操作 -->
          <template v-if="isAdmin">
            <el-button
              v-if="p.ready"
              size="small"
              @click="openReview(p)"
            >校对答案</el-button>
            <el-button
              v-if="p.status === 'pending'"
              type="primary"
              size="small"
              plain
              @click="review(p, 'approve')"
            >通过</el-button>
            <el-button
              v-if="p.status === 'pending'"
              size="small"
              type="danger"
              plain
              @click="reject(p)"
            >驳回</el-button>
            <el-button
              v-if="p.status === 'approved' && p.gen_status === 'failed'"
              size="small"
              @click="regenerate(p)"
            >重新生成</el-button>
          </template>

          <el-button
            v-if="isAdmin || p.uploader_id === userStore.user?.id"
            size="small"
            type="danger"
            text
            @click="remove(p)"
          >删除</el-button>
        </div>
      </div>
    </div>

    <!-- 校对标准答案 -->
    <el-dialog v-model="reviewVisible" :title="`校对标准答案 · ${reviewTitle}`" width="920px" top="6vh">
      <div class="review-tip">
        AI 识别出的答案可能有误。这里改完立即生效：判分用它，做题页也会同步重新生成。
        选择题填字母（多选如 <b>AB</b>），填空/计算题填参考答案要点。
      </div>
      <el-table :data="reviewItems" height="520" size="small" v-loading="reviewLoading">
        <el-table-column prop="no" label="题号" width="58" align="center" />
        <el-table-column label="题型" width="82">
          <template #default="{ row }">{{ typeText(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="title" label="题干" min-width="200" show-overflow-tooltip />
        <el-table-column label="标准答案" min-width="230">
          <template #default="{ row }">
            <el-input
              v-model="row.answer"
              type="textarea"
              :rows="2"
              size="small"
              placeholder="留空则该题不计分"
              @change="saveItem(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="解析" min-width="210">
          <template #default="{ row }">
            <el-input
              v-model="row.analysis"
              type="textarea"
              :rows="2"
              size="small"
              placeholder="可空"
              @change="saveItem(row)"
            />
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <span class="review-foot">共 {{ reviewItems.length }} 题 · 修改后自动保存</span>
        <el-button type="primary" @click="reviewVisible = false">完成</el-button>
      </template>
    </el-dialog>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadVisible" title="上传试卷" width="520px" :close-on-click-modal="false">
      <el-form :model="form" label-position="top">
        <el-form-item label="试卷文件">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-remove="() => (file = null)"
            accept=".pdf,.txt,.md"
            style="width:100%;"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">把 PDF 拖到这里，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF / TXT / MD，单个不超过 20MB。扫描版（图片型）PDF 读不出文字，请先转成可复制的 PDF。
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="试卷名称">
          <el-input v-model="form.title" placeholder="如 2024年广东省普通高中学业水平选择性考试 化学" />
        </el-form-item>

        <div class="upload-grid">
          <el-form-item label="省份">
            <el-input v-model="form.province" placeholder="广东" />
          </el-form-item>
          <el-form-item label="年份">
            <el-input v-model="form.year" placeholder="2024" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="form.exam_type" style="width:100%;">
              <el-option label="高考真题" value="高考真题" />
              <el-option label="模拟题" value="模拟题" />
              <el-option label="联考" value="联考" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="时长（分钟）">
            <el-input-number v-model="form.duration" :min="10" :max="300" controls-position="right" style="width:100%;" />
          </el-form-item>
        </div>

        <el-form-item label="总分">
          <el-input-number v-model="form.total_score" :min="10" :max="300" :step="10" controls-position="right" style="width:100%;" />
        </el-form-item>

        <el-alert
          v-if="!isAdmin && !isTeacher"
          type="info"
          :closable="false"
          show-icon
          title="学生上传的试卷需要管理员审核通过后才会生成做题页"
        />
      </el-form>

      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, VideoPlay } from '@element-plus/icons-vue'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isAdmin = computed(() => (userStore.user?.role || '').toLowerCase() === 'admin')
const isTeacher = computed(() => ['admin', 'teacher'].includes((userStore.user?.role || '').toLowerCase()))

const list = ref([])
const loading = ref(false)
const pendingCount = ref(0)
const tab = ref('all')
let timer = null

const tabs = [
  { label: '全部', value: 'all' },
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
]

const statusText = (p) => {
  if (p.status === 'pending') return '待审核'
  if (p.status === 'rejected') return '已驳回'
  if (p.gen_status === 'done') return '可做题'
  if (p.gen_status === 'failed') return '生成失败'
  return '生成中'
}
const statusType = (p) => {
  if (p.status === 'pending') return 'warning'
  if (p.status === 'rejected') return 'danger'
  if (p.gen_status === 'done') return 'success'
  if (p.gen_status === 'failed') return 'danger'
  return 'info'
}

const progressColor = [
  { color: '#C7D2FE', percentage: 30 },
  { color: '#818CF8', percentage: 70 },
  { color: '#4F46E5', percentage: 100 },
]

const load = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const params = {}
    if (isAdmin.value && tab.value !== 'all') params.status = tab.value
    const res = await api.get('/papers', { params })
    list.value = res.items || []
    pendingCount.value = res.pending_count || 0
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

const setTab = (v) => { tab.value = v; load() }

/* ---------- 做题 ---------- */
const startPaper = (p) => {
  // 做题页是后端直出的 HTML，同源打开即可（内部会用 localStorage 里的 token 回传成绩）
  window.open(`/chem/api/v1/papers/${p.id}/page`, '_blank')
}

/* ---------- 上传 ---------- */
const uploadVisible = ref(false)
const uploading = ref(false)
const file = ref(null)
const form = reactive({
  title: '', province: '', year: '', exam_type: '高考真题', duration: 75, total_score: 100,
})

const openUpload = () => {
  file.value = null
  Object.assign(form, { title: '', province: '', year: '', exam_type: '高考真题', duration: 75, total_score: 100 })
  uploadVisible.value = true
}

const onFileChange = (f) => {
  file.value = f.raw
  if (!form.title && f.name) form.title = f.name.replace(/\.[^.]+$/, '')
}

const submitUpload = async () => {
  if (!file.value) return ElMessage.warning('请先选择试卷文件')
  if (!form.title.trim()) return ElMessage.warning('请填写试卷名称')

  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('title', form.title.trim())
  fd.append('province', form.province || '')
  fd.append('year', form.year || '')
  fd.append('exam_type', form.exam_type)
  fd.append('duration', form.duration)
  fd.append('total_score', form.total_score)

  uploading.value = true
  try {
    const res = await api.post('/papers/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(res.message || '上传成功')
    uploadVisible.value = false
    await load()
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    uploading.value = false
  }
}

/* ---------- 校对答案 ---------- */
const reviewVisible = ref(false)
const reviewLoading = ref(false)
const reviewTitle = ref('')
const reviewItems = ref([])
let reviewPaperId = null

const typeText = (t) =>
  ({ single: '单选', multiple: '多选', fill: '填空', calculation: '计算', subjective: '简答' }[t] || t)

const openReview = async (p) => {
  reviewPaperId = p.id
  reviewTitle.value = p.title
  reviewVisible.value = true
  reviewLoading.value = true
  try {
    const res = await api.get(`/papers/${p.id}/questions`)
    reviewItems.value = res.items || []
  } catch (e) {
    reviewVisible.value = false
  } finally {
    reviewLoading.value = false
  }
}

const saveItem = async (row) => {
  try {
    await api.patch(`/papers/${reviewPaperId}/questions/${row.no}`, {
      answer: row.answer,
      analysis: row.analysis,
    })
    ElMessage.success(`第 ${row.no} 题已保存`)
  } catch (e) {
    // 失败原因由拦截器提示，这里不再重复弹
  }
}

/* ---------- 管理员 ---------- */
const review = async (p, action) => {
  try {
    const fd = new FormData()
    fd.append('action', action)
    fd.append('note', '')
    const res = await api.post(`/papers/${p.id}/review`, fd)
    ElMessage.success(res.message || '已通过')
    load(true)
  } catch (e) { /* ignore */ }
}

const reject = async (p) => {
  try {
    const { value } = await ElMessageBox.prompt('填写驳回原因（会显示给上传者）', '驳回试卷', {
      inputPlaceholder: '如：图片型 PDF，无法提取文字',
      inputValidator: (v) => (v && v.trim() ? true : '请填写原因'),
    })
    const fd = new FormData()
    fd.append('action', 'reject')
    fd.append('note', value.trim())
    await api.post(`/papers/${p.id}/review`, fd)
    ElMessage.success('已驳回')
    load(true)
  } catch (e) { /* 取消 */ }
}

const regenerate = async (p) => {
  try {
    await api.post(`/papers/${p.id}/regenerate`)
    ElMessage.success('已重新开始生成')
    load(true)
  } catch (e) { /* ignore */ }
}

const remove = async (p) => {
  try {
    await ElMessageBox.confirm(`确定删除《${p.title}》？题目会保留在题库里。`, '删除套卷', { type: 'warning' })
    await api.delete(`/papers/${p.id}`)
    ElMessage.success('已删除')
    load()
  } catch (e) { /* 取消 */ }
}

onMounted(() => {
  load()
  // 生成是后台任务，有未完成的就每 2 秒刷新一次（进度条要跟得上）
  timer = setInterval(() => {
    if (list.value.some((p) => ['waiting', 'running'].includes(p.gen_status))) load(true)
  }, 2000)
})
onUnmounted(() => timer && clearInterval(timer))
</script>

<style scoped>
.paper-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}
.paper-tabs__btn {
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: .15s;
}
.paper-tabs__btn.on { background: var(--bg-secondary); color: var(--text-primary); box-shadow: var(--shadow-xs); font-weight: 600; }
.paper-tabs__badge {
  background: var(--danger-color);
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  padding: 0 5px;
  border-radius: 99px;
}

.paper-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  padding: 16px 18px;
  margin-bottom: 12px;
  transition: .15s;
}
.paper-card:hover { border-color: var(--brand-300); }
.paper-card__main { flex: 1; min-width: 0; }
.paper-card__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.paper-card__title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.paper-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 7px;
  font-size: 12.5px;
  color: var(--text-placeholder);
}
.paper-card__err {
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--danger-deep, #B91C1C);
  background: var(--danger-light, #FEF2F2);
  border-radius: 8px;
  padding: 6px 10px;
}

/* 生成进度 */
.gen-box { margin-top: 10px; max-width: 520px; }
.gen-box__row { display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px; }
.gen-box__txt { font-size: 12.5px; color: var(--text-secondary); }
.gen-box__pct {
  margin-left: auto; font-size: 12px; color: var(--badge, #4F46E5);
  font-variant-numeric: tabular-nums; font-weight: 600;
}
.gen-logs { margin-top: 6px; display: flex; flex-direction: column; gap: 1px; }
.gen-logs__item { font-size: 11.5px; color: var(--text-placeholder); line-height: 1.6; }
.gen-logs__t { color: var(--text-disabled, #CBD5E1); margin-right: 6px; font-variant-numeric: tabular-nums; }
.paper-card__actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
.paper-card__actions .el-button { margin: 0; }

.upload-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }

.review-tip {
  font-size: 12.5px;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-bottom: 12px;
  line-height: 1.7;
}
.review-foot { float: left; font-size: 12.5px; color: var(--text-placeholder); line-height: 32px; }

@media (max-width: 768px) {
  .paper-card { flex-direction: column; align-items: stretch; }
  .paper-card__actions { justify-content: flex-start; }
  .upload-grid { grid-template-columns: 1fr; }
}
</style>
