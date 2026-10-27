<template>
  <div class="app-container">
    <div class="page-head">
      <div>
        <div class="page-head__title">📈 学习报告</div>
        <div class="page-head__desc">基于你每一次真实做题记录的数据分析</div>
      </div>
      <el-button plain size="small" @click="$router.push('/practice-history')">做题历史 →</el-button>
    </div>

    <!-- 概览卡 -->
    <div class="ov-grid">
      <div class="ov-card">
        <div class="ov-icon" style="background:var(--brand-50);color:var(--brand-600);">⚡</div>
        <div><div class="ov-num">{{ stats.today_count }}</div><div class="ov-label">今日做题</div></div>
      </div>
      <div class="ov-card">
        <div class="ov-icon" style="background:#ECFDF5;color:#059669;">🔥</div>
        <div><div class="ov-num">{{ stats.streak_days }}<span class="ov-unit">天</span></div><div class="ov-label">连续学习</div></div>
      </div>
      <div class="ov-card">
        <div class="ov-icon" style="background:#EFF6FF;color:#2563EB;">📚</div>
        <div><div class="ov-num">{{ stats.total_questions }}</div><div class="ov-label">累计做题</div></div>
      </div>
      <div class="ov-card">
        <div class="ov-icon" style="background:#FFFBEB;color:#D97706;">🎯</div>
        <div><div class="ov-num">{{ stats.accuracy }}<span class="ov-unit">%</span></div><div class="ov-label">总正确率</div></div>
      </div>
    </div>

    <!-- 趋势图 -->
    <el-card class="page-card" style="margin-bottom:16px;">
      <template #header>
        <div class="card-head">
          <span>近 {{ trend.length }} 天做题趋势</span>
          <span class="legend">
            <i class="dot" style="background:var(--brand-500);"></i>做题量
            <i class="dot" style="background:var(--success-color);"></i>正确率
          </span>
        </div>
      </template>
      <svg v-if="hasTrendData" viewBox="0 0 720 250" class="trend-svg" preserveAspectRatio="xMidYMid meet">
        <!-- 网格与右轴刻度 -->
        <g v-for="g in gridLines" :key="g.y">
          <line :x1="padL" :y1="g.y" :x2="720 - padR" :y2="g.y" stroke="var(--border-light)" stroke-width="1" />
          <text :x="720 - padR + 6" :y="g.y + 4" font-size="11" fill="var(--text-placeholder)">{{ g.label }}</text>
        </g>
        <!-- 柱：做题量 -->
        <g v-for="(d, i) in trend" :key="'bar' + i">
          <rect
            :x="xAt(i) - barW / 2" :y="yBar(d.total)" :width="barW"
            :height="barH - yBar(d.total)" rx="3"
            fill="var(--brand-500)" opacity="0.85">
            <title>{{ d.date }} · 做题 {{ d.total }} · 正确率 {{ d.accuracy }}%</title>
          </rect>
          <text v-if="showLabel(i)" :x="xAt(i)" :y="barH + 18" text-anchor="middle" font-size="11" fill="var(--text-placeholder)">{{ d.date.slice(5) }}</text>
        </g>
        <!-- 折线：正确率 -->
        <polyline
          :points="accPoints" fill="none"
          stroke="var(--success-color)" stroke-width="2.5"
          stroke-linejoin="round" stroke-linecap="round" />
        <g v-for="(d, i) in trend" :key="'pt' + i">
          <circle :cx="xAt(i)" :cy="yAcc(d.accuracy)" r="3.5" fill="var(--success-color)">
            <title>{{ d.date }} · 正确率 {{ d.accuracy }}%</title>
          </circle>
        </g>
      </svg>
      <el-empty v-else :image-size="60" description="近两周还没有做题记录，去刷几道题吧" />
    </el-card>

    <!-- 知识点掌握度 + 热力图 -->
    <el-row :gutter="16" style="margin-bottom:16px;">
      <el-col :xs="24" :md="14">
        <el-card class="page-card h-full">
          <template #header>
            <div class="card-head">
              <span>知识点掌握度</span>
              <el-tag v-if="kp.weak_points?.length" type="danger" size="small" effect="plain">
                薄弱 {{ kp.weak_points.length }} 个
              </el-tag>
            </div>
          </template>
          <div v-if="kp.details?.length" class="kp-list">
            <div v-for="d in kpShown" :key="d.knowledge_point" class="kp-item">
              <div class="kp-top">
                <span class="kp-name" :title="d.knowledge_point">{{ d.knowledge_point }}</span>
                <span class="kp-acc" :style="{color: accColor(d.accuracy)}">{{ d.accuracy }}%</span>
              </div>
              <div class="kp-bar">
                <div class="kp-fill" :style="{width: d.accuracy + '%', background: accColor(d.accuracy)}"></div>
              </div>
              <div class="kp-meta">
                <span>做过 {{ d.total_done }} 题 · 对 {{ d.correct_count }}</span>
                <span class="kp-tag" :class="'m' + d.level">{{ d.mastery }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else :image-size="60" description="暂无做题数据" />
          <div v-if="kp.details?.length > kpLimit" style="text-align:center;margin-top:10px;">
            <el-button text size="small" type="primary" @click="kpLimit = kpLimit === 8 ? 99 : 8">
              {{ kpLimit === 8 ? `展开全部 ${kp.details.length} 个知识点` : '收起' }}
            </el-button>
          </div>
          <div v-if="kp.weak_points?.length" style="margin-top:14px;padding-top:14px;border-top:1px dashed var(--border-light);display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="font-size:13px;color:var(--text-secondary);">建议优先复习：{{ kp.weak_points.slice(0, 3).join('、') }}</span>
            <el-button type="primary" size="small" @click="$router.push('/practice')">去刷题</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="10">
        <el-card class="page-card h-full">
          <template #header>
            <div class="card-head">
              <span>学习活跃度</span>
              <span style="font-size:12px;color:var(--text-placeholder);">{{ heat.active_days }}/{{ heat.cells?.length || 0 }} 天</span>
            </div>
          </template>
          <div class="heatmap" v-if="heat.cells?.length">
            <div class="heat-grid">
              <div v-for="(w, wi) in heatWeeks" :key="'pad' + wi" class="heat-cell" style="opacity:0.12;"></div>
              <div
                v-for="c in heat.cells" :key="c.date"
                class="heat-cell"
                :style="{ background: heatColor(c.count) }"
                :title="`${c.date} · ${c.count} 题`"
              ></div>
            </div>
            <div class="heat-legend">
              <span>少</span>
              <i v-for="n in [0, 1, 3, 6, 10]" :key="n" class="heat-cell" :style="{ background: heatColor(n === 0 ? 0 : (n === 1 ? 1 : n === 3 ? 3 : n === 6 ? 6 : 10)) }"></i>
              <span>多</span>
            </div>
          </div>
          <el-empty v-else :image-size="60" description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近记录 -->
    <el-card class="page-card">
      <template #header>
        <div class="card-head">
          <span>最近做题</span>
          <el-button text type="primary" size="small" @click="$router.push('/practice-history')">全部记录 →</el-button>
        </div>
      </template>
      <el-empty v-if="!recent.length" :image-size="60" description="还没有做题记录" />
      <div v-for="r in recent" :key="r.id" class="recent-item">
        <el-tag size="small" :type="r.is_correct ? 'success' : 'danger'" effect="plain">{{ r.is_correct ? '✓' : '✗' }}</el-tag>
        <span class="recent-title">{{ r.question_title }}</span>
        <span v-if="r.knowledge_point" class="recent-kp">{{ r.knowledge_point }}</span>
        <span class="recent-time">{{ r.submitted_at?.replace('T', ' ').slice(5, 16) }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/api'

const stats = reactive({ total_questions: 0, correct_count: 0, accuracy: 0, avg_time_spent: 0, today_count: 0, streak_days: 0 })
const trend = ref([])
const kp = ref({ details: [], weak_points: [] })
const heat = ref({ cells: [], active_days: 0 })
const recent = ref([])
const kpLimit = ref(8)

const hasTrendData = computed(() => trend.value.some(d => d.total > 0))
const kpShown = computed(() => (kp.value.details || []).slice(0, kpLimit.value))

/* ---- SVG 趋势图几何 ---- */
const padL = 8, padR = 40, barH = 175
const N = computed(() => Math.max(trend.value.length, 1))
const padR2 = 720 - padR - 10
const xAt = (i) => padL + 14 + (i * (padR2 - padL - 14)) / Math.max(N.value - 1, 1)
const barW = computed(() => Math.min(26, (padR2 - padL - 14) / N.value * 0.55))
const maxTotal = computed(() => Math.max(1, ...trend.value.map(d => d.total)))
const yBar = (v) => barH - (v / maxTotal.value) * (barH - 20)
const yAcc = (v) => 20 + (1 - v / 100) * (barH - 40)
const accPoints = computed(() => trend.value.map((d, i) => `${xAt(i)},${yAcc(d.accuracy)}`).join(' '))
const showLabel = (i) => trend.value.length <= 8 || i % 2 === 0
const gridLines = [
  { y: yAcc(0), label: '0%' },
  { y: yAcc(50), label: '50%' },
  { y: yAcc(100), label: '100%' },
]

/* ---- 热力图 ---- */
const heatWeeks = computed(() => {
  const cells = heat.value.cells || []
  if (!cells.length) return 0
  const first = new Date(cells[0].date + 'T00:00:00')
  return (first.getDay() + 6) % 7  // 周一=0，第一列前置空格数
})
const heatColor = (count) => {
  if (!count) return 'var(--bg-tertiary)'
  if (count <= 2) return 'rgba(79,70,229,0.25)'
  if (count <= 5) return 'rgba(79,70,229,0.45)'
  if (count <= 9) return 'rgba(79,70,229,0.7)'
  return 'rgba(79,70,229,1)'
}
const accColor = (a) => (a >= 80 ? 'var(--success-color)' : a >= 60 ? 'var(--warning-color)' : 'var(--danger-color)')

onMounted(async () => {
  const [s, t, k, h, r] = await Promise.allSettled([
    api.get('/practice-records/stats'),
    api.get('/practice-records/trend', { params: { days: 14 } }),
    api.get('/practice-records/knowledge'),
    api.get('/practice-records/heatmap', { params: { days: 91 } }),
    api.get('/practice-records', { params: { page: 1, page_size: 5 } }),
  ])
  if (s.status === 'fulfilled') Object.assign(stats, s.value.data)
  if (t.status === 'fulfilled') trend.value = t.value.data.trend || []
  if (k.status === 'fulfilled') kp.value = k.value.data
  if (h.status === 'fulfilled') heat.value = h.value.data
  if (r.status === 'fulfilled') recent.value = r.value.data.items || []
})
</script>

<style scoped>
/* 概览卡 */
.ov-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.ov-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-primary, var(--bg-color));
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md, 12px);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(15, 23, 42, 0.05));
}
.ov-icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.ov-num {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.ov-unit { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-left: 2px; }
.ov-label { font-size: 12px; color: var(--text-placeholder); margin-top: 2px; }

.card-head { display: flex; justify-content: space-between; align-items: center; }
.legend { font-size: 12px; color: var(--text-secondary); display: inline-flex; align-items: center; gap: 5px; }
.legend .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-left: 8px; }

.trend-svg { width: 100%; height: auto; display: block; }

/* 知识点掌握度 */
.h-full { height: 100%; }
.kp-list { display: flex; flex-direction: column; gap: 13px; }
.kp-item { min-width: 0; }
.kp-top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.kp-name {
  font-size: 13.5px; font-weight: 600; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.kp-acc { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.kp-bar {
  height: 7px; border-radius: 4px; background: var(--bg-tertiary);
  margin-top: 6px; overflow: hidden;
}
.kp-fill { height: 100%; border-radius: 4px; transition: width 0.6s var(--ease-out, ease); }
.kp-meta {
  display: flex; justify-content: space-between; margin-top: 4px;
  font-size: 11.5px; color: var(--text-placeholder);
}
.kp-tag { font-weight: 600; }
.kp-tag.m1 { color: var(--danger-color); }
.kp-tag.m2 { color: var(--warning-color); }
.kp-tag.m3 { color: var(--success-color); }

/* 热力图 */
.heat-grid {
  display: grid;
  grid-template-rows: repeat(7, 13px);
  grid-auto-flow: column;
  grid-auto-columns: 13px;
  gap: 3px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.heat-cell {
  width: 13px; height: 13px; border-radius: 3px;
  background: var(--bg-tertiary);
  display: inline-block;
}
.heat-legend {
  display: flex; align-items: center; gap: 4px;
  margin-top: 10px; font-size: 11px; color: var(--text-placeholder);
}

/* 最近记录 */
.recent-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 2px; border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}
.recent-item:last-child { border-bottom: none; }
.recent-title {
  flex: 1; min-width: 0; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.recent-kp { color: var(--text-placeholder); font-size: 12px; flex-shrink: 0; }
.recent-time { color: var(--text-placeholder); font-size: 12px; flex-shrink: 0; font-variant-numeric: tabular-nums; }

@media (max-width: 768px) {
  .ov-grid { grid-template-columns: repeat(2, 1fr); }
  .ov-num { font-size: 22px; }
}
</style>
