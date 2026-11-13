<template>
  <div class="app-container play-page">
    <div class="p-topbar">
      <el-button text @click="backToList">
        <el-icon><ArrowLeft /></el-icon>返回列表
      </el-button>
      <div class="p-topbar__right">
        <el-tag v-if="preview" type="warning" effect="light" size="small">试玩模式 · 不计入统计</el-tag>
        <el-button v-if="setInfo && !finished" text type="primary" @click="restart(true)">重新开始</el-button>
      </div>
    </div>

    <div v-if="loading" v-loading="true" class="p-loading"></div>

    <el-result
      v-else-if="error"
      icon="warning"
      title="关卡加载失败"
      :sub-title="error"
    >
      <template #extra>
        <el-button type="primary" @click="backToList">返回列表</el-button>
      </template>
    </el-result>

    <template v-else-if="setInfo">
      <div class="p-head">
        <div class="p-head__main">
          <div class="p-head__tags">
            <span class="p-tag" :class="'p-tag--' + setInfo.category">{{ setInfo.category_label }}</span>
            <span class="p-diff">{{ setInfo.difficulty_label }}</span>
            <span v-if="setInfo.grade" class="p-grade">{{ setInfo.grade }}</span>
          </div>
          <h1 class="p-title">{{ setInfo.title }}</h1>
          <p v-if="setInfo.description" class="p-desc">{{ setInfo.description }}</p>
        </div>
        <div class="p-stats">
          <div class="p-stat"><span>剩余</span><b>{{ remaining }}<small>/{{ totalPairs }}</small></b></div>
          <div class="p-stat"><span>用时</span><b>{{ timeText }}</b></div>
          <div class="p-stat"><span>错误</span><b>{{ mistakes }}</b></div>
          <div class="p-stat p-stat--score"><span>得分</span><b>{{ score }}</b></div>
        </div>
      </div>

      <div class="p-tip">
        <el-icon><MagicStick /></el-icon>
        先点一张卡，再点它对应的另一张；配对成功会显示相关知识点。
        <span v-if="combo >= 2" class="p-combo">连击 ×{{ combo }}</span>
      </div>

      <div class="p-board">
        <button
          v-for="card in cards"
          :key="card.key"
          type="button"
          class="p-card"
          :class="{
            'is-selected': first && first.key === card.key,
            'is-matched': card.matched,
            'is-wrong': card.wrong,
            'is-long': card.text.length > 30,
            'is-mid': card.text.length > 18 && card.text.length <= 30,
          }"
          @click="selectCard(card)"
        >
          <span class="p-card__text"><MathText :text="card.text" inline /></span>
        </button>
      </div>

      <div v-if="finished && !resultVisible" class="p-finished">
        <span>本局完成：{{ score }} 分 · 用时 {{ timeText }} · 错误 {{ mistakes }} 次</span>
        <div>
          <el-button @click="backToList">返回列表</el-button>
          <el-button type="primary" @click="restart">再来一局</el-button>
        </div>
      </div>

      <div class="p-knowledge" :class="{ 'is-empty': !lastMatch }">
        <div class="p-knowledge__head">
          <el-icon><Reading /></el-icon>{{ lastMatch ? '刚刚配对的知识点' : '知识点会显示在这里' }}
        </div>
        <template v-if="lastMatch">
          <div class="p-knowledge__pair">
            <span><MathText :text="lastMatch.left_text" inline /></span>
            <el-icon><Right /></el-icon>
            <span><MathText :text="lastMatch.right_text" inline /></span>
          </div>
          <div v-if="lastMatch.hint" class="p-knowledge__hint"><MathText :text="lastMatch.hint" /></div>
        </template>
        <div v-else class="p-knowledge__hint">
          化学连一连：物质与俗名、官能团与性质、方程式与现象、名称与化学式。
        </div>
      </div>
    </template>

    <el-dialog
      v-model="resultVisible"
      :close-on-click-modal="false"
      width="520px"
      class="result-dialog"
    >
      <div class="result">
        <div class="result__emoji">🎉</div>
        <div class="result__title">全部配对完成</div>
        <div class="result__score">{{ score }}<small>分</small></div>
        <div class="result__grid">
          <div><span>用时</span><b>{{ timeText }}</b></div>
          <div><span>错误</span><b>{{ mistakes }} 次</b></div>
          <div><span>最高连击</span><b>{{ maxCombo }}</b></div>
          <div><span>正确率</span><b>{{ accuracy }}%</b></div>
        </div>
        <div v-if="preview" class="result__note">试玩模式，本局成绩不计入统计</div>
        <div v-else-if="saved" class="result__note result__note--ok">成绩已记录</div>
        <div v-if="leaderboard.length" class="result__rank">
          <div class="result__rank-title">本关排行榜</div>
          <div
            v-for="row in leaderboard"
            :key="row.rank"
            class="result__row"
            :class="{ 'is-me': row.is_me }"
          >
            <span class="result__rank-no">{{ row.rank }}</span>
            <span class="result__rank-name">{{ row.name }}<i v-if="row.is_me">我</i></span>
            <span class="result__rank-score">{{ row.score }} 分</span>
            <span class="result__rank-time">{{ formatTime(row.duration_seconds) }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="backToList">返回列表</el-button>
        <el-button type="primary" @click="restart">再来一局</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import api from '@/api'
import MathText from '@/components/MathText.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const setInfo = ref(null)
const preview = computed(() => route.query.preview === '1')

const cards = ref([])
const first = ref(null)
const locked = ref(false)
const matchedCount = ref(0)
const mistakes = ref(0)
const score = ref(0)
const combo = ref(0)
const maxCombo = ref(0)
const seconds = ref(0)
const running = ref(false)
const finished = ref(false)
const lastMatch = ref(null)

const resultVisible = ref(false)
const leaderboard = ref([])
const saved = ref(false)

let ticker = null
let timers = []

const totalPairs = computed(() => setInfo.value?.pairs?.length || 0)
const remaining = computed(() => Math.max(0, totalPairs.value - matchedCount.value))
const accuracy = computed(() => {
  const tries = matchedCount.value + mistakes.value
  return tries ? Math.round((matchedCount.value / tries) * 100) : 100
})
const timeText = computed(() => formatTime(seconds.value))

function formatTime(value) {
  const total = Number(value) || 0
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function clearTimers() {
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
  timers.forEach((timer) => clearTimeout(timer))
  timers = []
}

function shuffle(list) {
  for (let i = list.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[list[i], list[j]] = [list[j], list[i]]
  }
  return list
}

function startGame() {
  clearTimers()
  const list = []
  for (const pair of setInfo.value.pairs) {
    list.push({ key: `p${pair.id}-l`, pairId: pair.id, text: pair.left_text, matched: false, wrong: false })
    list.push({ key: `p${pair.id}-r`, pairId: pair.id, text: pair.right_text, matched: false, wrong: false })
  }
  cards.value = shuffle(list)
  first.value = null
  locked.value = false
  matchedCount.value = 0
  mistakes.value = 0
  score.value = 0
  combo.value = 0
  maxCombo.value = 0
  seconds.value = 0
  lastMatch.value = null
  finished.value = false
  resultVisible.value = false
  leaderboard.value = []
  saved.value = false
  running.value = true

  ticker = setInterval(() => {
    if (!finished.value) seconds.value += 1
  }, 1000)
}

function selectCard(card) {
  if (!running.value || locked.value || card.matched) return
  if (first.value && first.value.key === card.key) {
    first.value = null
    return
  }
  if (!first.value) {
    first.value = card
    return
  }

  const firstCard = first.value
  locked.value = true

  if (firstCard.pairId === card.pairId) {
    const bonus = Math.min(combo.value, 5) * 2
    score.value += 10 + bonus
    combo.value += 1
    maxCombo.value = Math.max(maxCombo.value, combo.value)
    matchedCount.value += 1
    firstCard.matched = true
    card.matched = true
    lastMatch.value = setInfo.value.pairs.find((pair) => pair.id === card.pairId) || null
    first.value = null
    locked.value = false
    if (matchedCount.value === totalPairs.value) {
      timers.push(setTimeout(finishGame, 420))
    }
    return
  }

  mistakes.value += 1
  combo.value = 0
  score.value = Math.max(0, score.value - 3)
  firstCard.wrong = true
  card.wrong = true
  timers.push(setTimeout(() => {
    firstCard.wrong = false
    card.wrong = false
    first.value = null
    locked.value = false
  }, 520))
}

async function finishGame() {
  if (finished.value) return
  finished.value = true
  running.value = false
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
  resultVisible.value = true
  await submitRecord()
  await loadLeaderboard()
}

async function submitRecord() {
  if (preview.value) return
  try {
    await api.post(`/matching/sets/${setInfo.value.id}/records`, {
      score: score.value,
      mistakes: mistakes.value,
      pairs_total: totalPairs.value,
      max_combo: maxCombo.value,
      duration_seconds: Math.max(1, seconds.value),
    })
    saved.value = true
  } catch (e) {
    saved.value = false
  }
}

async function loadLeaderboard() {
  try {
    const res = await api.get(`/matching/sets/${setInfo.value.id}/leaderboard`, {
      params: { limit: 8 },
    })
    leaderboard.value = res.items || []
  } catch {
    leaderboard.value = []
  }
}

async function restart(confirmFirst = false) {
  if (confirmFirst && !finished.value) {
    try {
      await ElMessageBox.confirm('当前这局还没完成，确定重新开始吗？', '重新开始', {
        type: 'warning',
        confirmButtonText: '重新开始',
        cancelButtonText: '继续这局',
      })
    } catch {
      return
    }
  }
  startGame()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function backToList() {
  router.push('/matching')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.get(`/matching/sets/${route.params.id}`)
    if (!data.pairs || data.pairs.length < 2) {
      error.value = '这套关卡还没有配对内容'
      return
    }
    setInfo.value = data
    startGame()
  } catch (e) {
    error.value = '关卡不存在或已停用'
  } finally {
    loading.value = false
  }
}

onMounted(load)
onUnmounted(clearTimers)
</script>

<style scoped>
.play-page { padding-bottom: 40px; }
.p-topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.p-topbar__right { display: flex; align-items: center; gap: 8px; }

.p-loading { height: 320px; }

.p-head {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.p-head__main { flex: 1 1 420px; min-width: 0; }
.p-head__tags { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.p-tag {
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 3px 10px;
  background: #EEF2FF;
  color: #4338CA;
}
.p-tag--functional_group { background: #F5F3FF; color: #6D28D9; }
.p-tag--equation { background: #FFF7ED; color: #B45309; }
.p-tag--common_name { background: #ECFDF5; color: #047857; }
.p-tag--substance { background: #EFF6FF; color: #1D4ED8; }
.p-tag--mixed { background: #F1F5F9; color: #475569; }
.p-diff { font-size: 12px; color: var(--text-placeholder); }
.p-grade { font-size: 12px; color: var(--text-placeholder); }
.p-title { font-size: 23px; font-weight: 800; color: var(--text-primary); line-height: 1.35; margin: 0; }
.p-desc { color: var(--text-secondary); font-size: 13px; line-height: 1.7; margin: 8px 0 0; }

.p-stats { display: flex; gap: 8px; flex-wrap: wrap; }
.p-stat {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 8px 14px;
  min-width: 72px;
  text-align: center;
}
.p-stat span { display: block; font-size: 11px; color: var(--text-secondary); }
.p-stat b { display: block; font-size: 20px; color: var(--text-primary); margin-top: 2px; font-variant-numeric: tabular-nums; }
.p-stat b small { font-size: 12px; color: var(--text-placeholder); font-weight: 500; }
.p-stat--score { background: linear-gradient(135deg, #4F46E5, #6366F1); border-color: transparent; }
.p-stat--score span { color: #E0E7FF; }
.p-stat--score b { color: #fff; }

.p-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-tertiary);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  padding: 9px 14px;
  color: var(--text-secondary);
  font-size: 12.5px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.p-combo {
  margin-left: auto;
  font-weight: 800;
  color: #B45309;
  background: #FFF7ED;
  border-radius: 999px;
  padding: 2px 10px;
}

.p-board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.p-card {
  min-height: 96px;
  border-radius: 14px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  font-family: inherit;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.5;
  word-break: break-word;
  transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease, opacity .3s ease;
  position: relative;
}
.p-card:hover { border-color: var(--brand-300); box-shadow: 0 6px 18px rgba(79, 70, 229, .10); }
.p-card.is-mid .p-card__text { font-size: 13px; }
.p-card.is-long .p-card__text { font-size: 11.5px; line-height: 1.55; }
.p-card.is-selected {
  border-color: var(--brand-500);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, .18);
  transform: translateY(-2px);
}
.p-card.is-wrong {
  border-color: #EF4444;
  background: #FEF2F2;
  animation: shake .42s;
}
.p-card.is-matched {
  opacity: 0;
  transform: scale(.82);
  pointer-events: none;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(6px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}

.p-knowledge {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--brand-500);
  border-radius: 12px;
  padding: 14px 16px;
}
.p-knowledge.is-empty { border-left-color: var(--border-strong); }
.p-knowledge__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.p-knowledge__pair {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.p-knowledge__pair .el-icon { color: var(--brand-500); }
.p-knowledge__hint { margin-top: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.7; }

.p-finished {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  color: #047857;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 14px;
  font-weight: 600;
}

.result { text-align: center; padding: 4px 4px 0; }
.result__emoji { font-size: 34px; line-height: 1; }
.result__title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-top: 6px; }
.result__score { font-size: 46px; font-weight: 900; color: var(--brand-600); line-height: 1.1; margin: 6px 0 4px; }
.result__score small { font-size: 14px; color: var(--text-secondary); margin-left: 4px; font-weight: 600; }
.result__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 14px 0;
}
.result__grid div {
  background: var(--bg-tertiary);
  border-radius: 10px;
  padding: 8px 4px;
}
.result__grid span { display: block; font-size: 11px; color: var(--text-secondary); }
.result__grid b { display: block; font-size: 16px; color: var(--text-primary); margin-top: 3px; }
.result__note { font-size: 12px; color: var(--text-placeholder); }
.result__note--ok { color: #059669; }
.result__rank { margin-top: 16px; text-align: left; }
.result__rank-title { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.result__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
}
.result__row.is-me { background: var(--brand-50); color: var(--brand-700); font-weight: 700; }
.result__rank-no { width: 20px; font-weight: 800; color: var(--text-placeholder); }
.result__rank-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result__rank-name i { font-style: normal; font-size: 10px; background: var(--brand-600); color: #fff; border-radius: 4px; padding: 0 4px; margin-left: 4px; }
.result__rank-score { font-weight: 700; color: var(--text-primary); }
.result__rank-time { width: 54px; text-align: right; color: var(--text-placeholder); }

@media (max-width: 640px) {
  .p-board { grid-template-columns: repeat(2, 1fr); gap: 9px; }
  .p-card { min-height: 88px; padding: 10px; font-size: 13px; }
  .p-card.is-long .p-card__text { font-size: 10.5px; }
  .p-stats { width: 100%; }
  .p-stat { flex: 1; min-width: 0; }
  .p-title { font-size: 19px; }
  .result__grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
