<template>
  <div class="register-page">
    <div class="register-card">
      <!-- 顶部Logo和标题 -->
      <div class="login-header">
        <div class="logo-box">⚗️</div>
        <div class="header-text">
          <div class="title">化学学习助手 · ChemLearn</div>
          <div class="subtitle">学习的新境界</div>
        </div>
      </div>

      <!-- Tab切换 -->
      <div class="login-tabs">
        <div class="tab" @click="$router.push('/login')">登录</div>
        <div class="tab active">注册</div>
        <div class="tab">忘记密码</div>
      </div>

      <!-- 注册表单 -->
      <el-form :model="form" :rules="rules" ref="formRef">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <el-input v-model="form.username" placeholder="3-64个字符" class="dark-input" />
        </div>
        <div class="form-item">
          <label class="form-label">密码</label>
          <el-input v-model="form.password" type="password" placeholder="至少6位，需包含字母和数字" show-password class="dark-input" />
        </div>
        <div class="form-item">
          <label class="form-label">姓名</label>
          <el-input v-model="form.full_name" placeholder="真实姓名（用于错题导出）" class="dark-input" />
        </div>
        <div class="form-item">
          <label class="form-label">学段</label>
          <el-select v-model="form.grade" placeholder="选择学段" class="dark-select" style="width:100%;">
            <el-option label="高一" value="高一" />
            <el-option label="高二" value="高二" />
            <el-option label="高三" value="高三" />
          </el-select>
        </div>
        <div class="form-item">
          <label class="form-label">邮箱（选填）</label>
          <el-input v-model="form.email" placeholder="可选" class="dark-input" />
        </div>
        <el-button class="login-btn" :loading="loading" @click="handleRegister">注 册</el-button>
      </el-form>
      <div class="bottom-link">
        已有账号？<span @click="$router.push('/login')">去登录</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ username: '', password: '', full_name: '', grade: '', email: '' })
const rules = {
  username: [{ required: true, min: 3, max: 64, message: '用户名3-64个字符', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

const handleRegister = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    await userStore.register(form)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: var(--bg-primary);
}
.register-page::before,
.register-page::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: .5;
  pointer-events: none;
}
.register-page::before { width: 440px; height: 440px; background: #C7D2FE; top: -170px; left: -130px; }
.register-page::after { width: 360px; height: 360px; background: #A5F3FC; bottom: -150px; right: -90px; }

.register-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: 38px 36px 30px;
  animation: cardIn .55s var(--ease-out) both;
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(22px) scale(.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.login-header {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 24px;
}
.logo-box {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--gradient-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 25px;
  flex-shrink: 0;
  box-shadow: var(--shadow-brand-sm);
}
.header-text .title { font-size: 19px; font-weight: 800; color: var(--text-primary); letter-spacing: -0.02em; }
.header-text .subtitle { font-size: 12.5px; color: var(--text-tertiary); margin-top: 2px; }

.login-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  padding: 4px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  margin-bottom: 22px;
}
.tab {
  text-align: center;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-tertiary);
  padding: 9px 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--dur) var(--ease);
}
.tab:hover { color: var(--brand-600); }
.tab.active {
  background: var(--gradient-brand);
  color: #fff;
  box-shadow: var(--shadow-brand-sm);
}

.form-item { margin-bottom: 16px; }
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 7px;
}

.dark-input :deep(.el-input__wrapper),
.dark-select :deep(.el-select__wrapper) {
  background: var(--bg-secondary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
  border-radius: var(--radius-md);
  transition: box-shadow var(--dur) var(--ease);
}
.dark-input :deep(.el-input__wrapper:hover),
.dark-select :deep(.el-select__wrapper:hover) { box-shadow: 0 0 0 1px var(--border-strong) inset; }
.dark-input :deep(.el-input__wrapper.is-focus),
.dark-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--brand-500) inset, var(--ring) !important;
}
.dark-input :deep(.el-input__inner) { color: var(--text-primary); height: 40px; font-size: 14px; }
.dark-input :deep(.el-input__inner::placeholder) { color: var(--text-placeholder); }
.dark-input :deep(.el-input__suffix) { color: var(--text-placeholder); }
.dark-select :deep(.el-select__placeholder) { color: var(--text-placeholder); }
.dark-select :deep(.el-select__selected-item) { color: var(--text-primary); }

.login-btn {
  width: 100%;
  height: 46px;
  margin-top: 8px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--gradient-brand);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 3px;
  box-shadow: var(--shadow-brand-sm);
  transition: all var(--dur) var(--ease);
}
.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand);
  background: var(--gradient-brand);
  color: #fff;
}
.login-btn:active { transform: translateY(0); }

.bottom-link {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-tertiary);
}
.bottom-link span { color: var(--brand-600); cursor: pointer; font-weight: 600; }
.bottom-link span:hover { color: var(--brand-700); }

@media (max-width: 420px) {
  .register-page { padding: 14px; }
  .register-card { padding: 28px 20px 22px; }
  .header-text .title { font-size: 17px; }
}
</style>
