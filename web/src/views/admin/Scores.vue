<template>
  <div class="app-container">
    <div class="page-head">
      <div>
        <div class="page-head__title">成绩管理</div>
        <div class="page-head__desc">查看学生套卷 / 考试成绩，可直接修改得分</div>
      </div>
    </div>

    <el-card class="page-card">
      <div class="score-filters">
        <el-select v-model="kind" style="width: 130px;" @change="reload">
          <el-option label="套卷成绩" value="paper" />
          <el-option label="考试成绩" value="exam" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="学生姓名 / 账号 / 套卷或考试名称"
          clearable
          style="width: 320px;"
          @keyup.enter="reload"
        />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <span class="score-total">共 {{ total }} 条</span>
      </div>

      <el-table :data="items" v-loading="loading" style="width:100%;">
        <el-table-column label="学生" min-width="150">
          <template #default="{ row }">
            <b>{{ row.student_name }}</b>
            <span class="score-username">{{ row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="套卷 / 考试" min-width="240" show-overflow-tooltip />
        <el-table-column label="得分" width="150">
          <template #default="{ row }">
            <span class="score-value">{{ row.score }}</span>
            <span class="score-max"> / {{ row.total_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ formatTime(row.submitted_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">修改分数</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && items.length === 0" description="暂无成绩记录" />
      <div class="score-pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>

    <el-dialog v-model="editVisible" title="修改学生分数" width="420px">
      <div v-if="editing" class="edit-box">
        <div class="edit-row"><span>学生</span><b>{{ editing.student_name }}</b></div>
        <div class="edit-row"><span>项目</span><b>{{ editing.title }}</b></div>
        <div class="edit-row"><span>类型</span><b>{{ editing.kind === 'paper' ? '套卷' : '考试' }}</b></div>
        <div class="edit-row"><span>满分</span><b>{{ editing.total_score }}</b></div>
        <div class="edit-row">
          <span>得分</span>
          <el-input-number v-model="editScore" :min="0" :max="editing.total_score || 0" />
        </div>
        <p class="edit-tip">修改后学生报告、排行榜和成绩统计会读取新分数。</p>
      </div>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveScore">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const kind = ref('paper')
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const items = ref([])
const loading = ref(false)

const editVisible = ref(false)
const editing = ref(null)
const editScore = ref(0)
const saving = ref(false)

const formatTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

const load = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/scores', {
      params: { kind: kind.value, keyword: keyword.value, page: page.value, page_size: pageSize },
    })
    items.value = res.items || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

const reload = () => {
  page.value = 1
  load()
}

const reset = () => {
  keyword.value = ''
  page.value = 1
  load()
}

const openEdit = (row) => {
  editing.value = row
  editScore.value = Number(row.score || 0)
  editVisible.value = true
}

const saveScore = async () => {
  if (!editing.value) return
  if (editScore.value < 0 || editScore.value > (editing.value.total_score || 0)) {
    ElMessage.warning(`分数需在 0 - ${editing.value.total_score} 之间`)
    return
  }
  saving.value = true
  try {
    await api.put(`/admin/scores/${editing.value.kind}/${editing.value.id}`, {
      score: editScore.value,
    })
    ElMessage.success('分数已修改')
    editVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.score-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.score-total { margin-left: auto; color: var(--text-placeholder); font-size: 13px; }
.score-username { margin-left: 8px; color: var(--text-placeholder); font-size: 12px; }
.score-value { color: var(--brand-600); font-size: 18px; font-weight: 600; }
.score-max { color: var(--text-placeholder); font-size: 13px; }
.score-pager { display: flex; justify-content: flex-end; margin-top: 16px; }
.edit-box { display: flex; flex-direction: column; gap: 12px; }
.edit-row { display: flex; align-items: center; gap: 12px; font-size: 14px; }
.edit-row > span { width: 44px; color: var(--text-placeholder); flex-shrink: 0; }
.edit-tip { margin: 4px 0 0; color: var(--text-placeholder); font-size: 12px; }
</style>
