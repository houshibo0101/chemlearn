<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div class="page-head">
      <div class="page-head__title">👤 个人中心</div>
    </div>

    <el-card class="page-card">
      <div class="profile-head">
        <el-avatar :size="66" style="background:var(--gradient-brand);font-size:25px;box-shadow:var(--shadow-brand-sm);">
          {{ userStore.user?.full_name?.[0] || userStore.user?.username?.[0] }}
        </el-avatar>
        <div style="min-width:0;">
          <div style="font-size:18px;font-weight:700;color:var(--text-primary);">{{ userStore.user?.full_name || userStore.user?.username }}</div>
          <div style="font-size:13px;color:var(--text-placeholder);margin-top:5px;display:flex;align-items:center;gap:8px;">
            <el-tag size="small" :type="roleTagType">{{ roleText }}</el-tag>
            <span v-if="userStore.user?.grade && userStore.user?.role === 'student'">{{ userStore.user.grade }}</span>
          </div>
        </div>
      </div>

      <el-form :model="form" label-width="80px" size="default">
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="学段" v-if="userStore.user?.role === 'student'">
          <el-select v-model="form.grade" placeholder="选择学段" style="width:100%;">
            <el-option label="高一" value="高一" />
            <el-option label="高二" value="高二" />
            <el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="form.password" type="password" show-password placeholder="不修改请留空" />
        </el-form-item>
        <el-form-item label="暗色模式">
          <el-switch v-model="darkMode" @change="onDarkChange" active-text="开启" inactive-text="关闭" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save" :loading="saving">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 学生学习统计 -->
    <el-card class="page-card" v-if="userStore.user?.role === 'student'">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>📊 学习统计</span>
          <el-button text type="primary" size="small" @click="$router.push('/practice-history')">做题历史 →</el-button>
        </div>
      </template>
      <div class="stat-grid">
        <div class="stat-box"><div class="stat-value">{{ pStats.total_questions }}</div><div class="stat-label">总做题</div></div>
        <div class="stat-box"><div class="stat-value" style="color:var(--success-color);">{{ pStats.correct_count }}</div><div class="stat-label">正确</div></div>
        <div class="stat-box"><div class="stat-value">{{ pStats.accuracy }}%</div><div class="stat-label">正确率</div></div>
        <div class="stat-box"><div class="stat-value" style="color:var(--warning-color);">{{ pStats.avg_time_spent }}s</div><div class="stat-label">平均用时</div></div>
      </div>
      <div class="quick-links">
        <el-button plain size="small" @click="$router.push('/wrong')">
          <el-icon><Warning /></el-icon>错题本 ({{ stats.wrong }})
        </el-button>
        <el-button plain size="small" @click="$router.push('/favorites')">
          <el-icon><Star /></el-icon>我的收藏
        </el-button>
        <el-button plain size="small" @click="$router.push('/practice-history')">
          <el-icon><History /></el-icon>做题历史
        </el-button>
      </div>
    </el-card>

    <el-card class="page-card" v-if="userStore.user?.role !== 'student'">
      <template #header><span style="font-weight:bold;">🔑 API开放平台</span></template>
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">你可以创建API Key，通过开放接口访问题库数据。</p>
      <el-button type="primary" size="small" @click="goToApiPlatform">管理API密钥</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { getTheme, setTheme } from '@/utils/theme'

const userStore = useUserStore()
const saving = ref(false)
const stats = reactive({ wrong: 0, answered: 0, accuracy: 0 })
const pStats = reactive({ total_questions: 0, correct_count: 0, accuracy: 0, avg_time_spent: 0 })
const darkMode = ref(getTheme() === 'dark')

const roleText = computed(() => {
  const role = userStore.user?.role
  if (role === 'admin') return '管理员'
  if (role === 'teacher') return '老师'
  return '学生'
})
const roleTagType = computed(() => {
  const role = userStore.user?.role
  if (role === 'admin') return 'danger'
  if (role === 'teacher') return 'warning'
  return 'primary'
})

const onDarkChange = (val) => {
  setTheme(val ? 'dark' : 'light')
}

const goToApiPlatform = () => {
  const token = userStore.token
  window.open(`/api-platform.html?token=${encodeURIComponent(token)}`, '_blank')
}

const form = reactive({
  username: userStore.user?.username || '',
  full_name: userStore.user?.full_name || '',
  grade: userStore.user?.grade || '',
  email: userStore.user?.email || '',
  password: '',
})

const save = async () => {
  saving.value = true
  try {
    const data = { full_name: form.full_name, grade: form.grade, email: form.email }
    if (form.password) data.password = form.password
    await userStore.updateProfile(data)
    ElMessage.success('保存成功')
    form.password = ''
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await api.get('/wrong-questions', { params: { page: 1, page_size: 1 } })
    stats.wrong = res.total
  } catch {}
  if (userStore.user?.role === 'student') {
    try {
      const res = await api.get('/practice-records/stats')
      Object.assign(pStats, res)
    } catch {}
  }
})
</script>

<style scoped>
.profile-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-light);
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-box {
  text-align: center;
  padding: 14px 8px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
}
.stat-box .stat-value { color: var(--brand-600); }
.quick-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}
.quick-links .el-button { margin-left: 0; width: 100%; }

@media (max-width: 560px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .quick-links { grid-template-columns: 1fr; }
}
</style>
