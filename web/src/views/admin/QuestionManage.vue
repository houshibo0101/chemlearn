<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2>🛠 题库管理</h2>
      <div>
        <el-button :icon="Download" @click="exportExcel" style="margin-right:8px;">导出题库</el-button>
        <el-button :icon="Upload" @click="triggerImport" style="margin-right:8px;">批量导入</el-button>
        <el-button :icon="Document" @click="downloadTemplate" style="margin-right:8px;">下载模板</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">上传题目</el-button>
        <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="handleImport" />
      </div>
    </div>

    <!-- 筛选 -->
    <el-card class="page-card">
      <el-form :inline="true" :model="filter" size="small">
        <el-form-item>
          <el-input v-model="filter.keyword" placeholder="搜索ID/编号/标题/知识点" clearable style="width:200px;" @keyup.enter="loadList" />
        </el-form-item>
        <el-form-item label="学段">
          <el-select v-model="filter.grade" clearable placeholder="全部" style="width:90px;">
            <el-option label="高一" value="高一" /><el-option label="高二" value="高二" /><el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="filter.difficulty" clearable placeholder="全部" style="width:90px;">
            <el-option label="简单" value="easy" /><el-option label="中等" value="medium" /><el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 题目列表 -->
    <el-card class="page-card" v-loading="loading">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="question_code" label="编号" width="90">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.question_code || 'Q' + String(row.id).padStart(4, '0') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="题目" min-width="200" show-overflow-tooltip />
        <el-table-column label="题型" width="80">
          <template #default="{ row }"><el-tag size="small">{{ typeText(row.question_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="难度" width="80">
          <template #default="{ row }"><el-tag size="small" :type="diffColor(row.difficulty)">{{ diffText(row.difficulty) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="grade" label="学段" width="70" />
        <el-table-column prop="knowledge_point" label="知识点" width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="text-align:center;margin-top:16px;">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" @current-change="loadList" />
      </div>
    </el-card>

    <!-- 编辑/创建弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑题目' : '上传题目'" width="90%" top="5vh">
      <el-form :model="form" label-width="90px" size="default">
        <el-form-item label="题目标题" required>
          <el-input v-model="form.title" type="textarea" :rows="2" placeholder="题干内容" />
        </el-form-item>
        <el-form-item label="题目详情">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="补充说明、材料等（可选）" />
        </el-form-item>
        <el-form-item label="题型">
          <el-select v-model="form.question_type" style="width:100%;">
            <el-option label="单选题" value="single" />
            <el-option label="多选题" value="multiple" />
            <el-option label="填空题" value="fill" />
            <el-option label="计算题" value="calculation" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-radio-group v-model="form.difficulty">
            <el-radio value="easy">简单</el-radio>
            <el-radio value="medium">中等</el-radio>
            <el-radio value="hard">困难</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="学段">
          <el-select v-model="form.grade" clearable placeholder="选择学段" style="width:100%;">
            <el-option label="高一" value="高一" /><el-option label="高二" value="高二" /><el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="form.knowledge_point" placeholder="如：氧化还原反应" />
        </el-form-item>
        <el-form-item v-if="form.question_type==='single' || form.question_type==='multiple'" label="选项">
          <div style="width:100%;">
            <div v-for="(opt, idx) in optionList" :key="idx" style="display:flex;gap:8px;margin-bottom:8px;">
              <el-input v-model="opt.key" style="width:60px;" :maxlength="2" />
              <el-input v-model="opt.text" placeholder="选项内容" />
              <el-button type="danger" :icon="Delete" circle @click="optionList.splice(idx,1)" />
            </div>
            <el-button type="primary" plain size="small" :icon="Plus" @click="optionList.push({key:'',text:''})">添加选项</el-button>
          </div>
        </el-form-item>
        <el-form-item label="正确答案" required>
          <el-input v-model="form.answer" type="textarea" :rows="2" :placeholder="form.question_type==='single'?'如：A':form.question_type==='multiple'?'如：A,C':'填写正确答案'" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="form.analysis" type="textarea" :rows="3" placeholder="解题思路和解析" />
        </el-form-item>
        <el-form-item label="题目图片">
          <div style="width:100%;">
            <div v-if="imageList.length > 0" style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px;">
              <div v-for="(img, idx) in imageList" :key="idx" style="position:relative;border:1px solid var(--border-strong);border-radius:4px;overflow:hidden;">
                <img :src="img" style="width:160px;height:120px;object-fit:contain;display:block;" @click="previewImage(img)" />
                <el-button type="danger" size="small" circle style="position:absolute;top:4px;right:4px;padding:0;width:24px;height:24px;" @click="removeImage(idx)">×</el-button>
              </div>
            </div>
            <el-upload
              :action="uploadUrl"
              :headers="uploadHeaders"
              :show-file-list="false"
              :on-success="handleImageSuccess"
              :before-upload="beforeImageUpload"
              accept="image/*"
            >
              <el-button type="primary" plain :icon="Upload">上传图片</el-button>
            </el-upload>
            <div style="color:var(--text-placeholder);font-size:12px;margin-top:6px;">支持jpg/png，上传后自动关联到本题</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Download, Upload, Document } from '@element-plus/icons-vue'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref(false)
const editId = ref(null)
const optionList = ref([])
const fileInput = ref(null)
const importing = ref(false)
const imageList = ref([])

const uploadUrl = computed(() => `${api.defaults.baseURL}/questions/upload-image`)
const uploadHeaders = computed(() => ({ 'Authorization': `Bearer ${localStorage.getItem('token')}` }))

const filter = reactive({ keyword: '', grade: '', difficulty: '' })

const form = reactive({
  title: '', content: '', question_type: 'single', difficulty: 'medium',
  grade: '', knowledge_point: '', options: '', answer: '', analysis: '', images: '',
})

const typeText = (t) => ({ single: '单选', multiple: '多选', fill: '填空', calculation: '计算' }[t] || t)
const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)
const diffColor = (d) => ({ easy: 'success', medium: 'warning', hard: 'danger' }[d] || '')

const loadList = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filter.keyword) params.keyword = filter.keyword
    if (filter.grade) params.grade = filter.grade
    if (filter.difficulty) params.difficulty = filter.difficulty
    const res = await api.get('/questions/admin', { params })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, { title: '', content: '', question_type: 'single', difficulty: 'medium', grade: '', knowledge_point: '', options: '', answer: '', analysis: '' })
  optionList.value = []
  imageList.value = []
}

const openCreate = () => {
  resetForm()
  editing.value = false
  editId.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editing.value = true
  editId.value = row.id
  Object.assign(form, {
    title: row.title, content: row.content || '', question_type: row.question_type,
    difficulty: row.difficulty, grade: row.grade || '', knowledge_point: row.knowledge_point || '',
    options: row.options || '', answer: row.answer, analysis: row.analysis || '',
  })
  try { optionList.value = row.options ? JSON.parse(row.options) : [] } catch { optionList.value = [] }
  try { imageList.value = row.images ? JSON.parse(row.images) : [] } catch { imageList.value = [] }
  dialogVisible.value = true
}

const beforeImageUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isImage) { ElMessage.error('只能上传图片文件'); return false }
  if (!isLt5M) { ElMessage.error('图片大小不能超过5MB'); return false }
  return true
}

const handleImageSuccess = (res) => {
  if (res && res.url) {
    imageList.value.push(res.url)
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error('上传失败：' + (res.detail || '未知错误'))
  }
}

const removeImage = (idx) => {
  imageList.value.splice(idx, 1)
}

const previewImage = (url) => {
  window.open(url, '_blank')
}

const save = async () => {
  if (!form.title.trim()) { ElMessage.warning('请输入题目标题'); return }
  if (!form.answer.trim()) { ElMessage.warning('请输入正确答案'); return }
  if (optionList.value.length > 0) {
    form.options = JSON.stringify(optionList.value.filter(o => o.key && o.text))
  }
  form.images = JSON.stringify(imageList.value)
  saving.value = true
  try {
    if (editing.value) {
      await api.put(`/questions/${editId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/questions', form)
      ElMessage.success('上传成功')
    }
    dialogVisible.value = false
    loadList()
  } finally {
    saving.value = false
  }
}

const remove = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这道题目吗？', '提示', { type: 'warning' })
    await api.delete(`/questions/${id}`)
    ElMessage.success('已删除')
    loadList()
  } catch {}
}

// 导出题库Excel
const exportExcel = async () => {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`${api.defaults.baseURL}/questions/admin/export/excel`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `题库_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败：' + e.message)
  }
}

const triggerImport = () => {
  fileInput.value?.click()
}

const downloadTemplate = () => {
  // 生成CSV模板（Excel可直接打开）
  const headers = ['题目标题', '题目内容', '题型(单选/多选/填空/计算)', '难度(简单/中等/困难)', '学段', '知识点', '选项(JSON)', '正确答案', '解析']
  const example = [
    '下列物质属于电解质的是', 'A.铜 B.氯化钠 C.酒精 D.蔗糖', '单选', '简单', '高一', '电解质', '[{"key":"A","text":"铜"},{"key":"B","text":"氯化钠"},{"key":"C","text":"酒精"},{"key":"D","text":"蔗糖"}]', 'B', '氯化钠在水溶液中能导电，是电解质'
  ]
  const csv = '\uFEFF' + [headers, example].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '题目导入模板.csv'
  a.click()
  window.URL.revokeObjectURL(url)
  ElMessage.success('模板已下载，用Excel打开编辑后保存为.xlsx再上传')
}

const handleImport = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.name.match(/\.(xlsx|xls)$/)) {
    ElMessage.error('请上传Excel文件(.xlsx/.xls)')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('token')
    const res = await fetch(`${api.defaults.baseURL}/questions/batch-import`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    const data = await res.json()
    if (res.ok) {
      ElMessage.success(data.message || `导入完成：成功${data.success}题，失败${data.failed}题`)
      if (data.errors && data.errors.length > 0) {
        ElMessageBox.alert(data.errors.join('\n'), '导入失败详情', { type: 'warning' })
      }
      loadList()
    } else {
      ElMessage.error(data.detail || '导入失败')
    }
  } catch (err) {
    ElMessage.error('导入失败：' + err.message)
  } finally {
    importing.value = false
    e.target.value = ''
  }
}

onMounted(loadList)
</script>
