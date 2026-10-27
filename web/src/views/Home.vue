<template>
  <div class="app-container" style="padding-bottom:80px;">
    <!-- 欢迎横幅 -->
    <div class="hero-banner">
      <div style="position:relative;z-index:1;">
        <h2 style="margin-bottom:6px;font-size:22px;">
          你好，{{ userStore.user?.full_name || userStore.user?.username }} 👋
        </h2>
        <p style="font-size:13.5px;margin:0;">
          今天也要加油学化学哦！{{ userStore.user?.grade ? `（${userStore.user.grade}）` : '' }}
        </p>
      </div>
    </div>

    <!-- 功能入口 -->
    <div class="home-grid">
      <el-card class="entry-card" shadow="hover" @click="$router.push('/practice')">
        <div class="entry-card__icon" style="background:linear-gradient(135deg,#EEF2FF,#E0E7FF);color:#4F46E5;">
          <el-icon><EditPen /></el-icon>
        </div>
        <div class="entry-card__title">开始刷题</div>
        <div class="entry-card__desc">海量化学题目</div>
      </el-card>

      <el-card class="entry-card" shadow="hover" @click="$router.push('/wrong')">
        <div class="entry-card__icon" style="background:linear-gradient(135deg,#FFFBEB,#FEF3C7);color:#F59E0B;">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="entry-card__title">错题本</div>
        <div class="entry-card__desc">错题共 {{ wrongCount }} 道</div>
      </el-card>

      <el-card class="entry-card" shadow="hover" @click="$router.push('/ai')">
        <div class="entry-card__icon" style="background:linear-gradient(135deg,#ECFDF5,#D1FAE5);color:#10B981;">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="entry-card__title">AI 问答</div>
        <div class="entry-card__desc">化学问题随时问</div>
      </el-card>

      <el-card class="entry-card" shadow="hover" @click="$router.push('/profile')">
        <div class="entry-card__icon" style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);color:#EF4444;">
          <el-icon><User /></el-icon>
        </div>
        <div class="entry-card__title">个人中心</div>
        <div class="entry-card__desc">管理你的信息</div>
      </el-card>
    </div>

    <!-- 管理员入口 -->
    <el-card v-if="userStore.isAdmin" class="page-card">
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:7px;">🛠 管理员功能</span>
      </template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/admin/dashboard')">数据看板</el-button>
        <el-button type="success" plain @click="$router.push('/admin/users')">账号管理</el-button>
        <el-button type="warning" plain @click="$router.push('/admin/questions')">题库管理</el-button>
        <el-button type="info" plain @click="$router.push('/admin/api-keys')">API 密钥管理</el-button>
        <el-button type="danger" plain @click="exportAll">导出全部错题 Excel</el-button>
      </el-space>
    </el-card>

    <!-- 学习小贴士 -->
    <el-card class="page-card">
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:7px;">💡 化学小贴士</span>
      </template>
      <div class="tip-list">
        <div class="tip-item"><span>🔬</span><p>记忆化学方程式时，先理解反应原理再背诵，事半功倍。</p></div>
        <div class="tip-item"><span>⚗️</span><p>做计算题时，注意单位换算和有效数字。</p></div>
        <div class="tip-item"><span>📝</span><p>错题要及时复习，建议每周回顾一次错题本。</p></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'

const userStore = useUserStore()
const wrongCount = ref(0)

onMounted(async () => {
  try {
    const res = await api.get('/wrong-questions', { params: { page: 1, page_size: 1 } })
    wrongCount.value = res.total
  } catch {}
})

const exportAll = () => {
  const token = localStorage.getItem('token')
  window.open(`/api/v1/wrong-questions/admin/export/excel?token=${token}`, '_blank')
}
</script>

<style scoped>
.home-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.home-grid :deep(.el-card__body) { padding: 20px 14px; }

.tip-list { display: flex; flex-direction: column; gap: 12px; }
.tip-item {
  display: flex;
  gap: 11px;
  align-items: flex-start;
  padding: 11px 14px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
}
.tip-item span { font-size: 17px; line-height: 1.5; }
.tip-item p { margin: 0; font-size: 13.5px; color: var(--text-secondary); }

@media (max-width: 900px) {
  .home-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 420px) {
  .home-grid { gap: 10px; }
}
</style>
