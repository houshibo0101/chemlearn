<template>
  <div class="app-container mm-page">
    <div class="mm-head">
      <div>
        <h1 class="mm-title">化学连连看 · 关卡管理</h1>
        <p class="mm-sub">创建配对关卡，学生按关卡挑战；支持手动录入或批量导入 Excel / CSV / TXT。</p>
      </div>
      <div class="mm-actions">
        <el-button @click="downloadTemplate">
          <el-icon style="margin-right:4px;"><Download /></el-icon>导入模板
        </el-button>
        <el-button @click="openImport">
          <el-icon style="margin-right:4px;"><Upload /></el-icon>批量导入
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon style="margin-right:4px;"><Plus /></el-icon>新建关卡
        </el-button>
      </div>
    </div>

    <div class="mm-filter">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索关卡名称"
        clearable
        style="width:220px;"
        @clear="reload"
        @keyup.enter="reload"
      />
      <el-select v-model="filters.category" placeholder="全部类别" clearable style="width:150px;" @change="reload">
        <el-option v-for="(label, key) in categories" :key="key" :label="label" :value="key" />
      </el-select>
      <el-button @click="reload"><el-icon><Search /></el-icon></el-button>
      <span class="mm-count">共 {{ total }} 套关卡</span>
    </div>

    <el-table v-loading="loading" :data="sets" stripe class="mm-table">
      <el-table-column label="关卡" min-width="230">
        <template #default="{ row }">
          <div class="mm-set">
            <div class="mm-set__title">{{ row.title }}</div>
            <div class="mm-set__desc">{{ row.description || '—' }}</div>
            <div class="mm-set__meta">{{ row.creator_name }} · {{ formatDate(row.updated_at) }}</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类别" width="100">
        <template #default="{ row }">
          <span class="mm-tag" :class="'mm-tag--' + row.category">{{ row.category_label }}</span>
        </template>
      </el-table-column>
      <el-table-column label="难度" width="70">
        <template #default="{ row }">{{ row.difficulty_label }}</template>
      </el-table-column>
      <el-table-column prop="pair_count" label="配对" width="62" align="center" />
      <el-table-column prop="play_count" label="人次" width="62" align="center" />
      <el-table-column label="平均分" width="75" align="center">
        <template #default="{ row }">{{ row.record_count ? row.avg_score : '—' }}</template>
      </el-table-column>
      <el-table-column label="正确率" width="75" align="center">
        <template #default="{ row }">{{ row.record_count ? row.avg_accuracy + '%' : '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="82">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
            {{ row.is_active ? '已发布' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="205" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link size="small" @click="preview(row)">试玩</el-button>
          <el-button link size="small" @click="openRecords(row)">记录</el-button>
          <el-button link type="danger" size="small" @click="removeSet(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && !sets.length"
      description="还没有创建关卡，点右上角「新建关卡」或「批量导入」开始"
    />

    <div v-if="total > pageSize" class="mm-pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="load"
      />
    </div>

    <!-- 新建 / 编辑 -->
    <el-dialog
      v-model="editorVisible"
      :title="form.id ? '编辑关卡' : '新建关卡'"
      width="900px"
      top="4vh"
      :close-on-click-modal="false"
    >
      <el-form label-width="76px" class="mm-form">
        <div class="mm-form__row">
          <el-form-item label="关卡名称" required class="mm-form__grow">
            <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="例如：物质与俗名" />
          </el-form-item>
        </div>
        <div class="mm-form__row">
          <el-form-item label="类别" class="mm-form__col">
            <el-select v-model="form.category" style="width:100%;">
              <el-option v-for="(label, key) in categories" :key="key" :label="label" :value="key" />
            </el-select>
          </el-form-item>
          <el-form-item label="难度" class="mm-form__col">
            <el-select v-model="form.difficulty" style="width:100%;">
              <el-option label="简单" value="easy" />
              <el-option label="中等" value="medium" />
              <el-option label="较难" value="hard" />
            </el-select>
          </el-form-item>
          <el-form-item label="学段" class="mm-form__col">
            <el-input v-model="form.grade" placeholder="如 高一（可选）" maxlength="32" />
          </el-form-item>
          <el-form-item label="发布" class="mm-form__col mm-form__col--sm">
            <el-switch v-model="form.is_active" />
          </el-form-item>
        </div>
        <el-form-item label="关卡说明">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="500" show-word-limit />
        </el-form-item>

        <el-form-item label="配对内容" required>
          <div class="mm-pairs">
            <div class="mm-pairs__head">
              <span></span>
              <span>左项（物质 / 官能团 / 方程式）</span>
              <span>右项（俗称 / 结构 / 现象）</span>
              <span>提示（可选）</span>
              <span></span>
            </div>
            <div v-for="(pair, index) in form.pairs" :key="index" class="mm-pairs__row">
              <span class="mm-pairs__no">{{ index + 1 }}</span>
              <el-input v-model="pair.left_text" maxlength="200" placeholder="例如：氢氧化钠" />
              <el-input v-model="pair.right_text" maxlength="200" placeholder="例如：烧碱、火碱" />
              <el-input v-model="pair.hint" maxlength="300" placeholder="配对成功后展示" />
              <el-button
                link
                type="danger"
                :disabled="form.pairs.length <= 1"
                @click="removePair(index)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="mm-pairs__foot">
              <el-button size="small" @click="addPair">
                <el-icon style="margin-right:4px;"><Plus /></el-icon>添加一对
              </el-button>
              <span class="mm-pairs__hint">当前 {{ validPairCount }} 对有效内容（至少 2 对，最多 30 对）</span>
              <span class="mm-pairs__hint" style="margin-left:auto;">支持自动化学式：<code>H2</code> → H₂，也支持 <code>$H_2SO_4$</code></span>
            </div>

            <el-collapse class="mm-bulk">
              <el-collapse-item title="批量粘贴（每行：左项 | 右项 | 提示）" name="bulk">
                <el-input
                  v-model="bulkText"
                  type="textarea"
                  :rows="5"
                  placeholder="氢氧化钠 | 烧碱、火碱、苛性钠 | NaOH，强碱&#10;碳酸钠 | 纯碱、苏打 | Na₂CO₃"
                />
                <div class="mm-bulk__actions">
                  <el-button size="small" type="primary" plain @click="applyBulk">解析并添加到下方</el-button>
                  <span class="mm-pairs__hint">支持竖线、制表符分隔；已有内容不会被清空</span>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">
          {{ form.id ? '保存修改' : '创建关卡' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入 -->
    <el-dialog v-model="importVisible" title="批量导入关卡" width="620px" :close-on-click-modal="false">
      <el-form label-width="76px">
        <el-form-item label="文件">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            :file-list="fileList"
            accept=".xlsx,.csv,.txt"
            style="width:100%;"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .xlsx / .csv / .txt；第一张表 A 列左项、B 列右项、C 列提示（可选），表头会自动跳过。
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="关卡名称">
          <el-input v-model="importForm.title" placeholder="留空则用文件名" maxlength="80" />
        </el-form-item>
        <div class="mm-form__row">
          <el-form-item label="类别" class="mm-form__col">
            <el-select v-model="importForm.category" style="width:100%;">
              <el-option v-for="(label, key) in categories" :key="key" :label="label" :value="key" />
            </el-select>
          </el-form-item>
          <el-form-item label="难度" class="mm-form__col">
            <el-select v-model="importForm.difficulty" style="width:100%;">
              <el-option label="简单" value="easy" />
              <el-option label="中等" value="medium" />
              <el-option label="较难" value="hard" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="说明">
          <el-input v-model="importForm.description" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 作答记录 -->
    <el-dialog v-model="recordsVisible" :title="`作答记录 · ${currentSet?.title || ''}`" width="760px">
      <el-table :data="records" size="small" stripe max-height="440">
        <el-table-column prop="student_name" label="学生" min-width="110" />
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="score" label="得分" width="80" />
        <el-table-column prop="mistakes" label="错误" width="70" />
        <el-table-column label="正确率" width="90">
          <template #default="{ row }">{{ row.accuracy }}%</template>
        </el-table-column>
        <el-table-column label="用时" width="85">
          <template #default="{ row }">{{ formatTime(row.duration_seconds) }}</template>
        </el-table-column>
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!records.length" description="还没有学生完成这套关卡" :image-size="80" />
      <div v-if="recordsTotal > recordsPageSize" class="mm-pager">
        <el-pagination
          v-model:current-page="recordsPage"
          :page-size="recordsPageSize"
          :total="recordsTotal"
          layout="prev, pager, next"
          small
          background
          @current-change="loadRecords"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const router = useRouter()

const categories = {
  substance: '物质名称',
  functional_group: '官能团',
  equation: '化学方程式',
  common_name: '俗名俗称',
  mixed: '综合',
}

const sets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const filters = ref({ keyword: '', category: '' })

const editorVisible = ref(false)
const saving = ref(false)
const bulkText = ref('')
const form = ref(emptyForm())

const importVisible = ref(false)
const importing = ref(false)
const importFile = ref(null)
const fileList = ref([])
const importForm = ref({ title: '', category: 'mixed', difficulty: 'medium', description: '' })

const recordsVisible = ref(false)
const records = ref([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsPageSize = 10
const currentSet = ref(null)

function emptyForm() {
  return {
    id: null,
    title: '',
    description: '',
    category: 'mixed',
    difficulty: 'medium',
    grade: '',
    is_active: true,
    pairs: [
      { left_text: '', right_text: '', hint: '' },
      { left_text: '', right_text: '', hint: '' },
      { left_text: '', right_text: '', hint: '' },
    ],
  }
}

const validPairCount = computed(() =>
  form.value.pairs.filter((p) => p.left_text.trim() && p.right_text.trim()).length
)

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatTime(value) {
  const s = Number(value) || 0
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/matching/manage/sets', {
      params: {
        page: page.value,
        page_size: pageSize,
        keyword: filters.value.keyword || undefined,
        category: filters.value.category || undefined,
      },
    })
    sets.value = res.items || []
    total.value = res.total || 0
  } catch {
    sets.value = []
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

function openCreate() {
  form.value = emptyForm()
  bulkText.value = ''
  editorVisible.value = true
}

async function openEdit(row) {
  try {
    const detail = await api.get(`/matching/sets/${row.id}`)
    form.value = {
      id: detail.id,
      title: detail.title,
      description: detail.description || '',
      category: detail.category,
      difficulty: detail.difficulty,
      grade: detail.grade || '',
      is_active: detail.is_active,
      pairs: (detail.pairs || []).map((p) => ({
        left_text: p.left_text,
        right_text: p.right_text,
        hint: p.hint || '',
      })),
    }
    if (!form.value.pairs.length) {
      form.value.pairs = [{ left_text: '', right_text: '', hint: '' }]
    }
    bulkText.value = ''
    editorVisible.value = true
  } catch {}
}

function addPair() {
  if (form.value.pairs.length >= 30) {
    ElMessage.warning('最多 30 对')
    return
  }
  form.value.pairs.push({ left_text: '', right_text: '', hint: '' })
}

function removePair(index) {
  form.value.pairs.splice(index, 1)
}

function applyBulk() {
  const lines = (bulkText.value || '').split(/\r?\n/)
  let added = 0
  for (const line of lines) {
    const raw = line.trim()
    if (!raw) continue
    const parts = raw.split(/\s*[|｜\t]\s*/)
    if (parts.length < 2) continue
    const [left, right, hint] = parts
    if (!left.trim() || !right.trim()) continue
    form.value.pairs.push({
      left_text: left.trim(),
      right_text: right.trim(),
      hint: (hint || '').trim(),
    })
    added += 1
    if (form.value.pairs.length > 30) break
  }
  if (!added) {
    ElMessage.warning('没有识别到内容，请确认每行使用 | 或制表符分隔左右两项')
    return
  }
  // 清掉开头预留的空行，避免提交时混入空配对
  form.value.pairs = form.value.pairs.filter(
    (p, i) => p.left_text.trim() || p.right_text.trim() || i >= form.value.pairs.length - 1
  )
  bulkText.value = ''
  ElMessage.success(`已添加 ${added} 对`)
}

function validateForm() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请填写关卡名称')
    return null
  }
  const pairs = form.value.pairs
    .map((p) => ({
      left_text: p.left_text.trim(),
      right_text: p.right_text.trim(),
      hint: p.hint.trim(),
    }))
    .filter((p) => p.left_text && p.right_text)

  if (pairs.length < 2) {
    ElMessage.warning('至少需要 2 对有效内容')
    return null
  }
  if (pairs.length > 30) {
    ElMessage.warning('最多 30 对')
    return null
  }
  const lefts = pairs.map((p) => p.left_text)
  const rights = pairs.map((p) => p.right_text)
  const dupLeft = lefts.find((x, i) => lefts.indexOf(x) !== i)
  const dupRight = rights.find((x, i) => rights.indexOf(x) !== i)
  if (dupLeft) {
    ElMessage.warning(`左项重复：${dupLeft}`)
    return null
  }
  if (dupRight) {
    ElMessage.warning(`右项重复：${dupRight}`)
    return null
  }
  if (pairs.some((p) => p.left_text === p.right_text)) {
    ElMessage.warning('左项和右项不能完全相同')
    return null
  }
  return {
    title: form.value.title.trim(),
    description: form.value.description.trim() || null,
    category: form.value.category,
    difficulty: form.value.difficulty,
    grade: form.value.grade.trim() || null,
    is_active: form.value.is_active,
    pairs,
  }
}

async function save() {
  const payload = validateForm()
  if (!payload) return
  saving.value = true
  try {
    if (form.value.id) {
      await api.put(`/matching/sets/${form.value.id}`, payload)
      ElMessage.success('已保存')
    } else {
      await api.post('/matching/sets', payload)
      ElMessage.success('关卡已创建')
    }
    editorVisible.value = false
    load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

async function removeSet(row) {
  try {
    await ElMessageBox.confirm(
      `删除「${row.title}」后，该关卡的配对和作答记录都会一起删除，确定吗？`,
      '删除关卡',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await api.delete(`/matching/sets/${row.id}`)
    ElMessage.success('已删除')
    load()
  } catch {}
}

function preview(row) {
  const target = router.resolve({
    name: 'MatchingPlay',
    params: { id: row.id },
    query: { preview: '1' },
  })
  window.open(target.href, '_blank')
}

async function openRecords(row) {
  currentSet.value = row
  recordsPage.value = 1
  recordsVisible.value = true
  await loadRecords()
}

async function loadRecords() {
  if (!currentSet.value) return
  try {
    const res = await api.get(`/matching/manage/sets/${currentSet.value.id}/records`, {
      params: { page: recordsPage.value, page_size: recordsPageSize },
    })
    records.value = res.items || []
    recordsTotal.value = res.total || 0
  } catch {
    records.value = []
  }
}

/* ---------------- 批量导入 ---------------- */

function openImport() {
  importForm.value = { title: '', category: 'mixed', difficulty: 'medium', description: '' }
  importFile.value = null
  fileList.value = []
  importVisible.value = true
}

function onFileChange(file) {
  importFile.value = file.raw || null
  fileList.value = [file]
}

function onFileRemove() {
  importFile.value = null
  fileList.value = []
}

async function submitImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  const fd = new FormData()
  fd.append('file', importFile.value)
  fd.append('title', importForm.value.title || '')
  fd.append('description', importForm.value.description || '')
  fd.append('category', importForm.value.category)
  fd.append('difficulty', importForm.value.difficulty)
  fd.append('is_active', 'true')

  importing.value = true
  try {
    const res = await api.post('/matching/import', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importVisible.value = false
    load()
    if (res.warnings && res.warnings.length) {
      ElMessageBox.alert(
        `<p>已导入 <b>${res.pair_count}</b> 对，以下内容被跳过：</p><ul style="padding-left:18px;line-height:1.8;">${res.warnings
          .map((w) => `<li>${w}</li>`)
          .join('')}</ul>`,
        '导入完成（部分跳过）',
        { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
      )
    } else {
      ElMessage.success(`导入成功，共 ${res.pair_count} 对`)
    }
  } catch {
    // 拦截器已提示
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  try {
    const blob = await api.get('/matching/import/template', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.download = '化学连连看-导入模板.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch {}
}

onMounted(load)
</script>

<style scoped>
.mm-page { padding-bottom: 40px; }
.mm-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.mm-title { font-size: 23px; font-weight: 800; color: var(--text-primary); margin: 0; }
.mm-sub { color: var(--text-secondary); font-size: 13px; margin-top: 6px; }
.mm-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.mm-filter { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.mm-count { color: var(--text-placeholder); font-size: 12px; margin-left: auto; }

.mm-table { border-radius: 12px; overflow: hidden; }
.mm-set__title { font-weight: 700; color: var(--text-primary); font-size: 13.5px; }
.mm-set__desc { font-size: 12px; color: var(--text-placeholder); margin-top: 3px; }
.mm-set__meta { font-size: 11px; color: var(--text-placeholder); margin-top: 4px; }
.mm-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 8px;
  background: #EEF2FF;
  color: #4338CA;
}
.mm-tag--functional_group { background: #F5F3FF; color: #6D28D9; }
.mm-tag--equation { background: #FFF7ED; color: #B45309; }
.mm-tag--common_name { background: #ECFDF5; color: #047857; }
.mm-tag--substance { background: #EFF6FF; color: #1D4ED8; }
.mm-tag--mixed { background: #F1F5F9; color: #475569; }
.mm-pager { display: flex; justify-content: center; margin-top: 16px; }

.mm-form__row { display: flex; gap: 10px; flex-wrap: wrap; }
.mm-form__grow { flex: 1 1 100%; }
.mm-form__col { flex: 1 1 180px; }
.mm-form__col--sm { flex: 0 0 auto; }

.mm-pairs { width: 100%; border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden; }
.mm-pairs__head {
  display: grid;
  grid-template-columns: 26px 1fr 1fr 1fr 32px;
  gap: 8px;
  padding: 8px 10px;
  font-size: 11px;
  color: var(--text-placeholder);
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-light);
}
.mm-pairs__row {
  display: grid;
  grid-template-columns: 26px 1fr 1fr 1fr 32px;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  border-bottom: 1px dashed var(--border-lighter);
}
.mm-pairs__row:last-of-type { border-bottom: none; }
.mm-pairs__no { font-size: 11px; color: var(--text-placeholder); text-align: center; }
.mm-pairs__foot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 8px 10px;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-light);
}
.mm-pairs__hint { font-size: 11.5px; color: var(--text-placeholder); }
.mm-pairs__hint code {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: 4px;
  padding: 0 4px;
  font-family: Consolas, monospace;
}
.mm-bulk { margin: 0 10px 10px; }
.mm-bulk :deep(.el-collapse-item__header) { font-size: 12px; color: var(--text-secondary); }
.mm-bulk__actions { display: flex; align-items: center; gap: 10px; margin-top: 8px; flex-wrap: wrap; }

@media (max-width: 720px) {
  .mm-pairs__head { display: none; }
  .mm-pairs__row { grid-template-columns: 24px 1fr 28px; }
  .mm-pairs__row > :nth-child(4) { grid-column: 2; }
  .mm-actions { width: 100%; }
  .mm-actions .el-button { flex: 1; }
}
</style>
