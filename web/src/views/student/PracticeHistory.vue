<template>
  <div class="app-container" style="padding-bottom:80px;">
    <h2 style="margin-bottom:16px;">📝 做题历史</h2>

    <!-- 统计概览 -->
    <el-card class="page-card" style="margin-bottom:16px;">
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-num">{{ stats.total_questions }}</div><div class="stat-label">总做题</div></div>
        <div class="stat-item"><div class="stat-num" style="color:var(--success-color);">{{ stats.correct_count }}</div><div class="stat-label">正确</div></div>
        <div class="stat-item"><div class="stat-num">{{ stats.accuracy }}%</div><div class="stat-label">正确率</div></div>
        <div class="stat-item"><div class="stat-num" style="color:var(--warning-color);">{{ stats.avg_time_spent }}s</div><div class="stat-label">平均用时</div></div>
      </div>
    </el-card>

    <!-- 最近7天趋势 -->
    <el-card class="page-card" style="margin-bottom:16px;" v-if="stats.weekly_trend && stats.weekly_trend.length">
      <template #header><span style="font-weight:bold;">📈 最近7天做题趋势</span></template>
      <div class="trend-chart">
        <div v-for="day in stats.weekly_trend" :key="day.date" class="trend-bar-wrap">
          <div class="trend-bar" :style="{height: Math.max(4, day.total * 8) + 'px'}">
            <span class="trend-num">{{ day.total }}</span>
          </div>
          <div class="trend-label">{{ day.date.slice(5) }}</div>
        </div>
      </div>
    </el-card>

    <!-- 筛选 -->
    <el-card class="page-card" style="margin-bottom:12px;">
      <el-form :inline="true" size="small">
        <el-form-item label="来源">
          <el-select v-model="filterSource" placeholder="全部" clearable style="width:120px;" @change="loadRecords">
            <el-option label="刷题" value="practice" />
            <el-option label="作业" value="assignment" />
            <el-option label="考试" value="exam" />
          </el-select>
        </el-form-item>
        <el-form-item label="题型">
          <el-select v-model="filterType" placeholder="全部" clearable style="width:120px;" @change="loadRecords">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multiple" />
            <el-option label="填空" value="fill" />
            <el-option label="计算" value="calculation" />
            <el-option label="简答" value="subjective" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="filterCorrect" placeholder="全部" clearable style="width:100px;" @change="loadRecords">
            <el-option label="正确" :value="1" />
            <el-option label="错误" :value="0" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-empty v-if="!loading && records.length === 0" description="暂无做题记录" />

    <div v-for="r in records" :key="r.id" class="record-card">
      <el-card class="page-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div style="flex:1;min-width:0;">
            <div style="margin-bottom:6px;">
              <el-tag size="small" :type="r.is_correct ? 'success' : 'danger'">{{ r.is_correct ? '✓ 正确' : '✗ 错误' }}</el-tag>
              <el-tag size="small" type="info" style="margin-left:6px;">{{ sourceText(r.source) }}</el-tag>
              <span style="margin-left:8px;font-size:12px;color:var(--text-placeholder);">{{ r.submitted_at?.replace('T', ' ').slice(0, 16) }}</span>
            </div>
            <div style="font-weight:600;font-size:14px;color:var(--text-primary);">{{ r.question_title }}</div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">
              <span>得分：{{ r.score }}/{{ r.total_score }}</span>
              <span style="margin-left:12px;">用时：{{ r.time_spent }}s</span>
              <span v-if="r.knowledge_point" style="margin-left:12px;">{{ r.knowledge_point }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div v-if="total > pageSize" style="text-align:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'

const records = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filterSource = ref('')
const filterType = ref('')
const filterCorrect = ref(null)
const stats = reactive({ total_questions: 0, correct_count: 0, accuracy: 0, avg_time_spent: 0, weekly_trend: [] })

const sourceText = (s) => ({ practice: '刷题', assignment: '作业', exam: '考试' }[s] || s)

const loadRecords = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filterSource.value) params.source = filterSource.value
    if (filterType.value) params.question_type = filterType.value
    if (filterCorrect.value !== null && filterCorrect.value !== '') params.is_correct = filterCorrect.value
    const res = await api.get('/practice-records', { params })
    records.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await api.get('/practice-records/stats')
    Object.assign(stats, res)
  } catch {}
}

onMounted(() => { loadStats(); loadRecords() })
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-item {
  text-align: center;
  padding: 14px 8px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
}
.stat-num {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--brand-600);
  font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 12px; color: var(--text-placeholder); margin-top: 4px; font-weight: 500; }
.record-card { margin-bottom: 10px; }
.trend-chart { display: flex; align-items: flex-end; gap: 12px; height: 130px; padding: 0 8px; }
.trend-bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.trend-bar {
  width: 100%; max-width: 36px;
  background: var(--gradient-brand);
  border-radius: 6px 6px 0 0;
  display: flex; align-items: flex-start; justify-content: center;
  min-height: 4px;
  transition: height 0.5s var(--ease-out);
  box-shadow: var(--shadow-brand-sm);
}
.trend-num { font-size: 11px; color: #fff; padding-top: 2px; font-weight: 600; }
.trend-label { font-size: 11px; color: var(--text-placeholder); margin-top: 6px; }

@media (max-width: 560px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .trend-chart { gap: 6px; }
}
</style>
