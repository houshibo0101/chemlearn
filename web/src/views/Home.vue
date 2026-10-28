<template>
  <div class="app-container">
    <!-- 页头 -->
    <div class="dash-head">
      <div>
        <div class="dash-head__title">
          {{ greeting }}，{{ displayName }}
        </div>
        <div class="dash-head__meta">
          <span>{{ todayText }}</span>
          <i class="dash-head__dot"></i>
          <span>{{ roleText }}</span>
          <i class="dash-head__dot"></i>
          <span>{{ subtitle }}</span>
        </div>
      </div>
      <el-button type="primary" size="large" @click="$router.push('/practice')">
        <el-icon style="margin-right:6px;"><EditPen /></el-icon>
        开始刷题
      </el-button>
    </div>

    <!-- 指标条 -->
    <div class="dash-stats">
      <div v-for="s in stats" :key="s.label" class="dash-stat" :class="{ 'dash-stat--accent': s.accent }">
        <div class="dash-stat__label">
          <el-icon :size="13"><component :is="s.icon" /></el-icon>
          {{ s.label }}
        </div>
        <div class="dash-stat__value">
          {{ s.value }}<small v-if="s.unit">{{ s.unit }}</small>
        </div>
        <div class="dash-stat__hint">{{ s.hint }}</div>
      </div>
    </div>

    <!-- 图表 + 快捷入口 -->
    <div class="dash-split">
      <div class="dash-card">
        <div class="dash-card__head">
          <div>
            <div class="dash-card__title">
              <el-icon :size="15"><TrendCharts /></el-icon>
              近 7 天练习
            </div>
            <div class="dash-card__sub" style="margin-top:4px;">
              共 {{ weekTotal }} 题 · 平均正确率 {{ weekAccuracy }}% · 日均 {{ avgTotal }} 题
            </div>
          </div>
          <span class="dash-card__link" @click="$router.push('/report')">
            学习报告 <el-icon :size="12"><ArrowRight /></el-icon>
          </span>
        </div>

        <div v-if="weekTotal > 0" class="chart">
          <div class="chart__area">
            <!-- 日均参考线 -->
            <div class="chart__avg" :style="{ bottom: avgBottom }"></div>
            <div
              v-for="(d, i) in trend"
              :key="d.date"
              class="chart__col"
              :title="`${d.weekday ? '周' + d.weekday : d.date} · ${d.total} 题 · 正确率 ${d.accuracy}%`"
            >
              <div
                class="chart__bar"
                :class="{ 'is-today': i === trend.length - 1 }"
                :style="{ height: barHeight(d.total) }"
              >
                <span v-if="d.total" class="chart__val">{{ d.total }}</span>
              </div>
            </div>
          </div>
          <div class="chart__labels">
            <span
              v-for="(d, i) in trend"
              :key="d.date"
              :class="{ 'is-today': i === trend.length - 1 }"
            >{{ d.weekday }}</span>
          </div>
          <div class="chart__legend">
            <span><i style="background:var(--brand-100);"></i>每日练习量</span>
            <span><i style="background:var(--brand-500);"></i>今天</span>
            <span><i class="chart__legend-dash"></i>日均水平</span>
          </div>
        </div>

        <div v-else class="dash-empty">
          还没有练习记录
          <div style="margin-top:2px;">从第一道题开始，这里就会出现你的学习曲线</div>
          <el-button type="primary" plain size="small" @click="$router.push('/practice')">去刷题</el-button>
        </div>
      </div>

      <div class="dash-card">
        <div class="dash-card__head">
          <div class="dash-card__title">
            <el-icon :size="15"><Grid /></el-icon>
            快捷入口
          </div>
        </div>
        <div class="quick-list">
          <div v-for="q in quickEntries" :key="q.title" class="quick-item" @click="$router.push(q.to)">
            <div class="quick-item__icon">
              <el-icon :size="17"><component :is="q.icon" /></el-icon>
            </div>
            <div class="quick-item__body">
              <div class="quick-item__title">{{ q.title }}</div>
              <div class="quick-item__desc">{{ q.desc }}</div>
            </div>
            <el-icon class="quick-item__arrow" :size="13"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理员功能 -->
    <div v-if="userStore.isAdmin" class="dash-card" style="margin-bottom:16px;">
      <div class="dash-card__head">
        <div class="dash-card__title">
          <el-icon :size="15"><Setting /></el-icon>
          管理后台
        </div>
        <span class="dash-card__sub">题库 {{ adminInfo.questions }} 题 · 用户 {{ adminInfo.users }} 人</span>
      </div>
      <div class="admin-row">
        <el-button type="primary" size="small" @click="$router.push('/admin/dashboard')">数据看板</el-button>
        <el-button size="small" @click="$router.push('/admin/users')">账号管理</el-button>
        <el-button size="small" @click="$router.push('/admin/questions')">题库管理</el-button>
        <el-button size="small" @click="$router.push('/admin/api-keys')">API 密钥</el-button>
        <el-button size="small" @click="exportAll">
          <el-icon style="margin-right:4px;"><Download /></el-icon>导出错题 Excel
        </el-button>
      </div>
    </div>

    <!-- 学习提示 -->
    <div class="dash-card">
      <div class="dash-card__head">
        <div class="dash-card__title">
          <el-icon :size="15"><Reading /></el-icon>
          学习提示
        </div>
      </div>
      <div class="tip-quote">
        <div v-for="(t, i) in tips" :key="i" class="tip-quote__item">
          <span class="tip-quote__no">{{ String(i + 1).padStart(2, '0') }}</span>
          <p class="tip-quote__text">{{ t }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'

const userStore = useUserStore()

const statsData = ref({
  total_questions: 0,
  accuracy: 0,
  today_count: 0,
  streak_days: 0,
  weekly_trend: [],
})
const adminInfo = ref({ users: 0, questions: 0, wrong: 0 })

const displayName = computed(() => userStore.user?.full_name || userStore.user?.username || '同学')
const isAdmin = computed(() => userStore.isAdmin)
const role = computed(() => userStore.user?.role)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  const w = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · 周${w}`
})

const roleText = computed(() => ({ student: '学生', teacher: '教师', admin: '管理员' }[role.value] || '用户'))
const subtitle = computed(() => (isAdmin.value ? '今天也来看看系统的运行情况' : '今天也要加油学化学哦'))
const grade = computed(() => userStore.user?.grade || '')

// ===== 指标条 =====
const stats = computed(() => {
  const s = statsData.value
  if (isAdmin.value) {
    return [
      { label: '题库题目', value: adminInfo.value.questions, unit: '题', icon: 'Files', hint: '全部学科题目总数' },
      { label: '注册用户', value: adminInfo.value.users, unit: '人', icon: 'UserFilled', hint: '含学生 / 教师 / 管理员' },
      { label: '错题记录', value: adminInfo.value.wrong, unit: '条', icon: 'Warning', hint: '全站错题累计' },
      { label: '今日练习', value: s.today_count, unit: '题', icon: 'EditPen', hint: '你自己的今日练习量', accent: true },
    ]
  }
  return [
    { label: '今日练习', value: s.today_count, unit: '题', icon: 'EditPen', hint: '今天完成的数量', accent: true },
    { label: '累计练习', value: s.total_questions, unit: '题', icon: 'Files', hint: '历史做题总数' },
    { label: '正确率', value: s.accuracy, unit: '%', icon: 'Aim', hint: '全部作答的正确比例' },
    { label: '连续学习', value: s.streak_days, unit: '天', icon: 'Sunny', hint: grade.value || '保持每日练习' },
  ]
})

// ===== 7 天趋势 =====
const trend = computed(() => {
  const raw = statsData.value.weekly_trend || []
  return raw.map((d) => {
    const dt = new Date(d.date)
    const w = Number.isNaN(dt.getTime()) ? '' : ['日', '一', '二', '三', '四', '五', '六'][dt.getDay()]
    return {
      date: d.date,
      total: d.total || 0,
      correct: d.correct || 0,
      accuracy: d.total ? Math.round((d.correct / d.total) * 100) : 0,
      weekday: w,
    }
  })
})

const maxTotal = computed(() => Math.max(1, ...trend.value.map((d) => d.total)))
const barHeight = (n) => (n ? `${Math.max(6, (n / maxTotal.value) * 100)}%` : '0%')

const weekTotal = computed(() => trend.value.reduce((a, d) => a + d.total, 0))
const weekCorrect = computed(() => trend.value.reduce((a, d) => a + d.correct, 0))
const weekAccuracy = computed(() =>
  weekTotal.value ? Math.round((weekCorrect.value / weekTotal.value) * 100) : 0
)

// 日均参考线：按同一纵向比例换算，保证与柱高对齐
const avgTotal = computed(() => (trend.value.length ? +(weekTotal.value / trend.value.length).toFixed(1) : 0))
const avgBottom = computed(() => `${Math.min(96, (avgTotal.value / maxTotal.value) * 100)}%`)

// ===== 快捷入口（按角色） =====
const quickEntries = computed(() => {
  if (role.value === 'student') {
    return [
      { title: '错题本', desc: '回顾做错的题，逐个击破', to: '/wrong', icon: 'Warning' },
      { title: 'AI 问答', desc: '把不会的题讲明白', to: '/ai', icon: 'ChatDotRound' },
      { title: '我的作业', desc: '查看待完成的作业', to: '/student/assignments', icon: 'Document' },
      { title: '学习报告', desc: '看正确率与知识点掌握', to: '/report', icon: 'DataLine' },
    ]
  }
  if (role.value === 'teacher') {
    return [
      { title: '班级管理', desc: '建班、邀请学生、看进度', to: '/teacher/classes', icon: 'School' },
      { title: '作业管理', desc: '布置与批改作业', to: '/teacher/assignments', icon: 'Document' },
      { title: '学生错题', desc: '按班级查看共性错题', to: '/teacher/wrong-questions', icon: 'Warning' },
      { title: '学习报告', desc: '班级维度的数据分析', to: '/report', icon: 'DataLine' },
    ]
  }
  return [
    { title: '错题本', desc: '全部错题与导出', to: '/wrong', icon: 'Warning' },
    { title: 'AI 问答', desc: '化学问题随时问', to: '/ai', icon: 'ChatDotRound' },
    { title: '班级管理', desc: '班级与学生概况', to: '/teacher/classes', icon: 'School' },
    { title: '学习报告', desc: '正确率与知识点掌握', to: '/report', icon: 'DataLine' },
  ]
})

const tips = [
  '记忆化学方程式时，先理解反应原理再背诵，事半功倍。',
  '做计算题时，注意单位换算和有效数字。',
  '错题要及时复习，建议每周回顾一次错题本。',
]

onMounted(async () => {
  try {
    const res = await api.get('/practice-records/stats')
    statsData.value = { ...statsData.value, ...res }
  } catch {}

  if (isAdmin.value) {
    try {
      const r = await api.get('/admin/dashboard/summary')
      adminInfo.value = {
        users: r?.users?.total || 0,
        questions: r?.questions?.total || 0,
        wrong: r?.wrong_questions?.total || 0,
      }
    } catch {}
  }
})

const exportAll = () => {
  const token = localStorage.getItem('token')
  window.open(`/api/v1/wrong-questions/admin/export/excel?token=${token}`, '_blank')
}
</script>
