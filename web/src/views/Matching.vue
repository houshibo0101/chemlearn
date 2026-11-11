<template>
  <div class="app-container matching-page">
    <div class="m-head">
      <div>
        <div class="m-head__title">
          化学连连看
          <span class="m-head__badge">配对挑战</span>
        </div>
        <div class="m-head__sub">
          物质、官能团、化学方程式、俗名俗称——把同一对的两张卡连起来，越快越准分越高
        </div>
      </div>
      <div class="m-head__actions">
        <el-button v-if="canManage" @click="$router.push('/matching/manage')">
          <el-icon style="margin-right:4px;"><Setting /></el-icon>管理关卡
        </el-button>
        <el-button @click="showRecords = true">
          <el-icon style="margin-right:4px;"><Clock /></el-icon>我的记录
        </el-button>
      </div>
    </div>

    <div class="m-stats">
      <div class="m-stat">
        <div class="m-stat__label"><el-icon><Collection /></el-icon>可玩关卡</div>
        <div class="m-stat__value">{{ total }}<small>套</small></div>
      </div>
      <div class="m-stat">
        <div class="m-stat__label"><el-icon><Trophy /></el-icon>我的最高分</div>
        <div class="m-stat__value">{{ summary.best_score }}<small>分</small></div>
      </div>
      <div class="m-stat">
        <div class="m-stat__label"><el-icon><Timer /></el-icon>我的挑战次数</div>
        <div class="m-stat__value">{{ summary.plays }}<small>次</small></div>
      </div>
    </div>

    <div class="m-filter">
      <el-radio-group v-model="category" @change="reload">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="(label, key) in categories" :key="key" :label="key">
          {{ label }}
        </el-radio-button>
      </el-radio-group>
      <el-input
        v-model="keyword"
        placeholder="搜索关卡名称"
        clearable
        class="m-search"
        @clear="reload"
        @keyup.enter="reload"
      >
        <template #append>
          <el-button @click="reload"><el-icon><Search /></el-icon></el-button>
        </template>
      </el-input>
    </div>

    <div v-loading="loading" class="m-grid">
      <div
        v-for="item in sets"
        :key="item.id"
        class="m-card"
        :class="'m-card--' + item.category"
        @click="openSet(item)"
      >
        <div class="m-card__top">
          <span class="m-tag" :class="'m-tag--' + item.category">{{ item.category_label }}</span>
          <span class="m-diff" :class="'m-diff--' + item.difficulty">{{ item.difficulty_label }}</span>
        </div>
        <div class="m-card__title">{{ item.title }}</div>
        <div class="m-card__desc">{{ item.description || '把左右两边的化学知识配成对' }}</div>
        <div class="m-card__meta">
          <span><el-icon><Grid /></el-icon>{{ item.pair_count }} 对</span>
          <span><el-icon><User /></el-icon>{{ item.play_count }} 人次</span>
          <span v-if="item.my_best !== null" class="m-card__best">最好 {{ item.my_best }} 分</span>
        </div>
        <div class="m-card__cta">
          {{ item.my_plays ? '再挑战一次' : '开始挑战' }}
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <el-empty
      v-if="!loading && !sets.length"
      :description="keyword || category ? '没有符合条件的关卡，换个筛选试试' : '还没有可玩的关卡，等老师上传后就能玩啦'"
    />

    <div v-if="total > pageSize" class="m-pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="load"
      />
    </div>

    <el-dialog v-model="showRecords" title="我的连连看记录" width="720px">
      <el-table :data="records" size="small" stripe max-height="420">
        <el-table-column prop="set_title" label="关卡" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category_label" label="类别" width="100" />
        <el-table-column prop="score" label="得分" width="80" />
        <el-table-column prop="mistakes" label="错误" width="70" />
        <el-table-column label="用时" width="90">
          <template #default="{ row }">{{ formatTime(row.duration_seconds) }}</template>
        </el-table-column>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!records.length" description="还没有挑战记录，选一套关卡开始吧" :image-size="80" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

const categories = {
  substance: '物质名称',
  functional_group: '官能团',
  equation: '方程式',
  common_name: '俗名俗称',
  mixed: '综合',
}

const sets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const category = ref('')
const keyword = ref('')
const loading = ref(false)
const showRecords = ref(false)
const records = ref([])
const summary = ref({ plays: 0, best_score: 0 })

const canManage = computed(() => ['teacher', 'admin'].includes(userStore.user?.role))

function formatTime(seconds) {
  const s = Number(seconds) || 0
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/matching/sets', {
      params: {
        page: page.value,
        page_size: pageSize,
        category: category.value || undefined,
        keyword: keyword.value || undefined,
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

function openSet(item) {
  router.push(`/matching/${item.id}`)
}

async function loadSummary() {
  try {
    const res = await api.get('/matching/my/summary')
    summary.value = res || { plays: 0, best_score: 0 }
  } catch {
    summary.value = { plays: 0, best_score: 0 }
  }
}

async function loadRecords() {
  try {
    const res = await api.get('/matching/my/records', { params: { page_size: 50 } })
    records.value = res.items || []
  } catch {
    records.value = []
  }
}

onMounted(() => {
  load()
  loadSummary()
  loadRecords()
})
</script>

<style scoped>
.matching-page { padding-bottom: 40px; }

.m-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.m-head__title {
  font-size: 25px;
  font-weight: 800;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
}
.m-head__badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--brand-700);
  background: var(--brand-100);
  border-radius: 999px;
  padding: 3px 10px;
  letter-spacing: .5px;
}
.m-head__sub { color: var(--text-secondary); font-size: 13px; margin-top: 6px; max-width: 620px; line-height: 1.6; }
.m-head__actions { display: flex; gap: 8px; }

.m-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.m-stat {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 14px 16px;
}
.m-stat__label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.m-stat__value { font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 6px; }
.m-stat__value small { font-size: 12px; font-weight: 500; color: var(--text-placeholder); margin-left: 4px; }

.m-filter { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 16px; }
.m-search { width: 240px; margin-left: auto; }

.m-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  min-height: 120px;
}
.m-card {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 16px 16px 14px;
  cursor: pointer;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
  overflow: hidden;
}
.m-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 3px;
  background: var(--brand-500);
  opacity: .85;
}
.m-card--functional_group::before { background: #8B5CF6; }
.m-card--equation::before { background: #F59E0B; }
.m-card--common_name::before { background: #10B981; }
.m-card--substance::before { background: #3B82F6; }
.m-card--mixed::before { background: #64748B; }
.m-card:hover {
  transform: translateY(-3px);
  border-color: var(--brand-300);
  box-shadow: 0 10px 26px rgba(79, 70, 229, .12);
}
.m-card__top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.m-tag {
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 3px 9px;
  background: #EEF2FF;
  color: #4338CA;
}
.m-tag--functional_group { background: #F5F3FF; color: #6D28D9; }
.m-tag--equation { background: #FFF7ED; color: #B45309; }
.m-tag--common_name { background: #ECFDF5; color: #047857; }
.m-tag--substance { background: #EFF6FF; color: #1D4ED8; }
.m-tag--mixed { background: #F1F5F9; color: #475569; }
.m-diff { font-size: 11px; color: var(--text-placeholder); }
.m-diff--easy { color: #059669; }
.m-diff--hard { color: #DC2626; }
.m-card__title { font-size: 16px; font-weight: 700; color: var(--text-primary); line-height: 1.45; }
.m-card__desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-top: 6px;
  line-height: 1.6;
  min-height: 40px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.m-card__meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-light);
}
.m-card__meta span { display: inline-flex; align-items: center; gap: 3px; }
.m-card__best { color: #B45309; font-weight: 700; }
.m-card__cta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 10px;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--brand-600);
}
.m-pager { display: flex; justify-content: center; margin-top: 20px; }

@media (max-width: 640px) {
  .m-stats { grid-template-columns: 1fr; }
  .m-grid { grid-template-columns: 1fr; }
  .m-search { width: 100%; margin-left: 0; }
  .m-head__actions { width: 100%; }
  .m-head__actions .el-button { flex: 1; }
}
</style>
