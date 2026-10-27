<template>
  <div class="dashboard-container">
    <!-- 快速跳转：顶部胶囊条 -->
    <div class="quick-nav">
      <span class="nav-title">快速跳转</span>
      <div class="nav-chips">
        <button class="nav-chip" @click="scrollTo('section-overview')">📈 总览</button>
        <button class="nav-chip" @click="scrollTo('section-users')">👥 用户分布</button>
        <button class="nav-chip" @click="scrollTo('section-questions')">📚 题目分布</button>
        <button class="nav-chip" @click="scrollTo('section-knowledge')">🧠 知识点</button>
        <button class="nav-chip" @click="scrollTo('section-wrong')">❌ 错题排行</button>
        <button class="nav-chip" @click="scrollTo('section-active')">🔥 活跃用户</button>
        <button class="nav-chip" @click="scrollTo('section-apikey')">🔑 API Key</button>
        <button class="nav-chip" @click="scrollTo('section-logs')">📋 调用日志</button>
      </div>
    </div>

    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <div class="page-head__title">📊 数据看板</div>
        <div class="page-head__desc">平台运营数据总览</div>
      </div>
      <el-button :icon="Refresh" @click="loadAll" :loading="loading">刷新数据</el-button>
    </div>

    <!-- 总览卡片 -->
    <div id="section-overview" class="section-anchor"></div>
    <div class="stat-grid">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background:linear-gradient(135deg,#EEF2FF,#E0E7FF);color:#4F46E5;">
          <el-icon :size="26"><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.users?.total || 0 }}</div>
          <div class="stat-label">总用户数</div>
          <div class="stat-sub">学生 {{ summary.users?.students || 0 }} · 老师 {{ summary.users?.teachers || 0 }}</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background:linear-gradient(135deg,#ECFDF5,#D1FAE5);color:#10B981;">
          <el-icon :size="26"><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.questions?.total || 0 }}</div>
          <div class="stat-label">题库总数</div>
          <div class="stat-sub">错题 {{ summary.wrong_questions?.total || 0 }} 道</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background:linear-gradient(135deg,#FFFBEB,#FEF3C7);color:#F59E0B;">
          <el-icon :size="26"><Key /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.api?.total_keys || 0 }}</div>
          <div class="stat-label">API Key 数</div>
          <div class="stat-sub">活跃 {{ summary.api?.active_keys || 0 }} · 调用 {{ summary.api?.total_calls || 0 }} 次</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);color:#EF4444;">
          <el-icon :size="26"><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ summary.users?.banned || 0 }}</div>
          <div class="stat-label">封禁 / 异常</div>
          <div class="stat-sub">封禁 {{ summary.users?.banned || 0 }} · 异常 {{ summary.users?.suspicious || 0 }}</div>
        </div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <div id="section-users" class="section-anchor"></div>
    <div class="chart-grid">
      <el-card shadow="hover">
        <template #header><span>👥 用户按学段分布</span></template>
        <div v-if="usersByGrade.length" class="bar-list">
          <div v-for="item in usersByGrade" :key="item.grade" class="bar-row">
            <span class="bar-label">{{ item.grade }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{width: getBarWidth(item.count, maxGradeCount) + '%', background: 'var(--gradient-brand)'}"></div>
            </div>
            <span class="bar-value">{{ item.count }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </el-card>

      <el-card shadow="hover" id="section-questions">
        <template #header><span>📚 题目按难度分布</span></template>
        <div v-if="questionsByDifficulty.length" class="bar-list">
          <div v-for="item in questionsByDifficulty" :key="item.difficulty" class="bar-row">
            <span class="bar-label">{{ item.difficulty }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{width: getBarWidth(item.count, maxDifficultyCount) + '%', background: getDifficultyColor(item.difficulty)}"></div>
            </div>
            <span class="bar-value">{{ item.count }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </el-card>

      <el-card shadow="hover" id="section-knowledge">
        <template #header><span>🧠 知识点分布 Top10</span></template>
        <div v-if="questionsByKnowledge.length" class="bar-list">
          <div v-for="item in questionsByKnowledge" :key="item.knowledge_point" class="bar-row">
            <span class="bar-label" :title="item.knowledge_point">{{ item.knowledge_point?.slice(0, 8) }}{{ item.knowledge_point?.length > 8 ? '...' : '' }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{width: getBarWidth(item.count, maxKnowledgeCount) + '%', background: 'linear-gradient(90deg,#8B5CF6,#A78BFA)'}"></div>
            </div>
            <span class="bar-value">{{ item.count }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </el-card>
    </div>

    <!-- 排行榜区域 -->
    <div id="section-wrong" class="section-anchor"></div>
    <div class="rank-grid">
      <el-card shadow="hover">
        <template #header><span>❌ 错题最多题目 Top10</span></template>
        <el-table :data="topWrongQuestions" size="small" max-height="300">
          <el-table-column prop="question_id" label="ID" width="60" />
          <el-table-column prop="title" label="题目" min-width="180" show-overflow-tooltip />
          <el-table-column prop="knowledge_point" label="知识点" width="100" show-overflow-tooltip />
          <el-table-column prop="total_wrong" label="错误次数" width="90" sortable />
          <el-table-column prop="user_count" label="出错人数" width="90" />
        </el-table>
      </el-card>

      <el-card shadow="hover" id="section-active">
        <template #header><span>🔥 最活跃用户 Top10</span></template>
        <el-table :data="topActiveUsers" size="small" max-height="300">
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="full_name" label="姓名" width="100" />
          <el-table-column prop="grade" label="学段" width="80" />
          <el-table-column prop="wrong_count" label="错题数" width="80" sortable />
          <el-table-column prop="total_wrong" label="总错误次数" width="100" sortable />
        </el-table>
      </el-card>
    </div>

    <!-- API Key统计 -->
    <div id="section-apikey" class="section-anchor"></div>
    <el-card shadow="hover" style="margin-bottom:16px;">
      <template #header><span>🔑 API Key 调用统计</span></template>
      <el-table :data="apiKeyStats" size="small">
        <el-table-column prop="name" label="Key 名称" width="150" />
        <el-table-column prop="username" label="所属用户" width="120" />
        <el-table-column prop="call_count" label="总调用次数" width="120" sortable />
        <el-table-column label="今日调用" width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.daily_limit ? Math.min(100, (row.daily_call_count / row.daily_limit) * 100) : 0" :stroke-width="10" />
            <span style="font-size:12px;color:var(--text-placeholder);">{{ row.daily_call_count }} / {{ row.daily_limit || '不限' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- API调用日志 -->
    <div id="section-logs" class="section-anchor"></div>
    <el-card shadow="hover">
      <template #header>
        <span>📋 API 调用日志（最近 50 条）</span>
      </template>
      <el-table :data="apiCallLogs" size="small" max-height="400">
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag :type="row.method === 'GET' ? 'success' : row.method === 'POST' ? 'primary' : 'warning'" size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="endpoint" label="接口" min-width="250" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column prop="api_key" label="API Key" width="120" />
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { Refresh, User, Collection, Key, Warning } from '@element-plus/icons-vue'

const loading = ref(false)
const summary = ref({})
const usersByGrade = ref([])
const questionsByDifficulty = ref([])
const questionsByKnowledge = ref([])
const topWrongQuestions = ref([])
const topActiveUsers = ref([])
const apiKeyStats = ref([])
const apiCallLogs = ref([])

const maxGradeCount = computed(() => Math.max(...usersByGrade.value.map(i => i.count), 1))
const maxDifficultyCount = computed(() => Math.max(...questionsByDifficulty.value.map(i => i.count), 1))
const maxKnowledgeCount = computed(() => Math.max(...questionsByKnowledge.value.map(i => i.count), 1))

const getBarWidth = (count, max) => Math.max(5, (count / max) * 100)

const getDifficultyColor = (diff) => {
  const colors = { '简单': '#10B981', '中等': '#F59E0B', '困难': '#EF4444' }
  return colors[diff] || '#4F46E5'
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

const scrollTo = (id) => {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

const loadAll = async () => {
  loading.value = true
  try {
    const [s1, s2, s3, s4, s5, s6, s7] = await Promise.all([
      api.get('/admin/dashboard/summary'),
      api.get('/admin/dashboard/users-by-grade'),
      api.get('/admin/dashboard/questions-by-difficulty'),
      api.get('/admin/dashboard/questions-by-knowledge'),
      api.get('/admin/dashboard/top-wrong-questions'),
      api.get('/admin/dashboard/top-active-users'),
      api.get('/admin/dashboard/api-key-stats'),
    ])
    summary.value = s1
    usersByGrade.value = s2.items || []
    questionsByDifficulty.value = s3.items || []
    questionsByKnowledge.value = s4.items || []
    topWrongQuestions.value = s5.items || []
    topActiveUsers.value = s6.items || []
    apiKeyStats.value = s7.items || []

    const logs = await api.get('/admin/dashboard/api-call-logs')
    apiCallLogs.value = logs.items || []
  } catch (e) {
    console.error('加载数据失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => loadAll())
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  max-width: 1280px;
  margin: 0 auto;
}

/* 快速跳转 —— 顶部胶囊条 */
.quick-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 18px;
  background: color-mix(in srgb, var(--bg-secondary) 90%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}
.nav-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-placeholder);
  flex-shrink: 0;
  padding-right: 12px;
  border-right: 1px solid var(--border-light);
  letter-spacing: 0.02em;
}
.nav-chips {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  scrollbar-width: none;
}
.nav-chips::-webkit-scrollbar { display: none; }
.nav-chip {
  flex-shrink: 0;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--dur) var(--ease);
}
.nav-chip:hover {
  background: var(--brand-50);
  border-color: var(--brand-300);
  color: var(--brand-600);
  transform: translateY(-1px);
}

/* 板块锚点 */
.section-anchor { scroll-margin-top: 84px; }

/* 统计卡片网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 18px;
}
.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-info { flex: 1; min-width: 0; }
.stat-value {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.15;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 2px; font-weight: 600; }
.stat-sub { font-size: 11.5px; color: var(--text-placeholder); margin-top: 2px; }

/* 图表网格 */
.chart-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
.rank-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px; }

.bar-list { display: flex; flex-direction: column; gap: 11px; }
.bar-row { display: flex; align-items: center; gap: 9px; }
.bar-label {
  width: 72px;
  font-size: 12.5px;
  color: var(--text-secondary);
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  flex: 1;
  height: 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.bar-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.5s var(--ease-out); }
.bar-value {
  width: 42px;
  text-align: right;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .chart-grid { grid-template-columns: 1fr; }
  .rank-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .dashboard-container { padding: 14px; }
  .nav-title { display: none; }
  .quick-nav { padding: 8px 10px; }
}
@media (max-width: 480px) {
  .stat-grid { grid-template-columns: 1fr; gap: 12px; }
}
</style>
