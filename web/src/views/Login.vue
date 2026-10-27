<template>
  <div class="auth-page">
    <!-- 背景光斑 -->
    <div class="auth-glow auth-glow--1"></div>
    <div class="auth-glow auth-glow--2"></div>
    <div class="auth-glow auth-glow--3"></div>

    <div class="auth-shell">
      <!-- 左侧品牌区 -->
      <aside class="auth-brand">
        <div class="auth-brand__inner">
          <div class="auth-brand__logo">⚗️</div>
          <h1 class="auth-brand__title">化学学习助手</h1>
          <p class="auth-brand__sub">ChemLearn · 让化学学习更有章法</p>

          <ul class="auth-brand__features">
            <li><span class="dot dot--1">📚</span>万道高考真题与知识点题库</li>
            <li><span class="dot dot--2">🎯</span>智能推题，精准补齐薄弱环节</li>
            <li><span class="dot dot--3">📈</span>学习报告，进步一目了然</li>
            <li><span class="dot dot--4">🤖</span>AI 答疑，随时解决疑难</li>
          </ul>
        </div>

        <!-- 装饰分子 -->
        <svg class="auth-deco" viewBox="0 0 200 200" fill="none" aria-hidden="true">
          <circle cx="60" cy="60" r="7" fill="rgba(255,255,255,.5)" />
          <circle cx="150" cy="90" r="5" fill="rgba(255,255,255,.35)" />
          <circle cx="95" cy="155" r="6" fill="rgba(255,255,255,.4)" />
          <path d="M60 60 L150 90 L95 155 Z" stroke="rgba(255,255,255,.28)" stroke-width="1.6" />
        </svg>
      </aside>

      <!-- 右侧表单区 -->
      <section class="auth-form-wrap">
        <header class="auth-head">
          <div class="auth-head__logo">⚗️</div>
          <div>
            <div class="auth-head__title">
              {{ activeTab === 'login' ? '欢迎回来' : '创建账号' }}
            </div>
            <div class="auth-head__sub">
              {{ activeTab === 'login' ? '登录后继续你的学习进度' : '填写信息，立刻开始学习' }}
            </div>
          </div>
        </header>

        <!-- 分段切换 -->
        <div class="auth-switch">
          <button class="auth-switch__btn" :class="{ active: activeTab === 'login' }" @click="switchTab('login')">登录</button>
          <button class="auth-switch__btn" :class="{ active: activeTab === 'register' }" @click="switchTab('register')">注册</button>
          <span class="auth-switch__thumb" :style="{ transform: activeTab === 'login' ? 'translateX(0)' : 'translateX(100%)' }"></span>
        </div>

        <!-- 登录表单 -->
        <div v-show="activeTab === 'login'" class="form-panel">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" @keyup.enter="handleLogin" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="loginForm.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" size="large" type="password" placeholder="请输入密码" show-password
                        :prefix-icon="Lock" @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button class="auth-submit" type="primary" size="large" :loading="loginLoading" @click="handleLogin">
              登 录
            </el-button>
          </el-form>
        </div>

        <!-- 注册表单 -->
        <div v-show="activeTab === 'register'" class="form-panel">
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" size="large" placeholder="3-64 个字符" :prefix-icon="User" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" size="large" type="password" placeholder="至少 6 位，需包含字母和数字" show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="registerForm.full_name" size="large" placeholder="真实姓名（用于错题导出）" :prefix-icon="Postcard" />
            </el-form-item>
            <el-form-item label="学段">
              <el-select v-model="registerForm.grade" size="large" placeholder="选择学段" style="width:100%;">
                <el-option label="高一" value="高一" />
                <el-option label="高二" value="高二" />
                <el-option label="高三" value="高三" />
              </el-select>
            </el-form-item>
            <el-form-item label="邮箱（选填）">
              <el-input v-model="registerForm.email" size="large" placeholder="可选" :prefix-icon="Message" />
            </el-form-item>
            <el-button class="auth-submit" type="primary" size="large" :loading="registerLoading" @click="handleRegister">
              注 册
            </el-button>
          </el-form>
          <div class="auth-foot">
            已有账号？<a @click="switchTab('login')">去登录</a>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock, Postcard, Message } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loginFormRef = ref()
const registerFormRef = ref()
const loginLoading = ref(false)
const registerLoading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', full_name: '', grade: '', email: '' })

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const registerRules = {
  username: [{ required: true, min: 3, max: 64, message: '用户名3-64个字符', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

const switchTab = (tab) => {
  activeTab.value = tab
}

const handleLogin = async () => {
  await loginFormRef.value.validate()
  loginLoading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/')
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  await registerFormRef.value.validate()
  registerLoading.value = true
  try {
    await userStore.register(registerForm)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '注册失败')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: var(--bg-primary);
}

/* 背景光斑 */
.auth-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.55;
  pointer-events: none;
}
.auth-glow--1 { width: 460px; height: 460px; background: #C7D2FE; top: -160px; left: -120px; }
.auth-glow--2 { width: 380px; height: 380px; background: #A5F3FC; bottom: -140px; right: -90px; }
.auth-glow--3 { width: 300px; height: 300px; background: #DDD6FE; bottom: 120px; left: 34%; opacity: 0.4; }
[data-theme='dark'] .auth-glow { opacity: 0.25; }

.auth-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 940px;
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: shellIn 0.6s var(--ease-out) both;
}
@keyframes shellIn {
  from { opacity: 0; transform: translateY(22px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* 左侧品牌面板 */
.auth-brand {
  position: relative;
  background: var(--gradient-brand-v);
  color: #fff;
  padding: 44px 36px;
  overflow: hidden;
  display: flex;
  align-items: center;
}
.auth-brand::after {
  content: '';
  position: absolute;
  width: 300px; height: 300px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  right: -130px; top: -110px;
}
.auth-brand__inner { position: relative; z-index: 1; width: 100%; }
.auth-brand__logo {
  width: 54px; height: 54px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.25);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  margin-bottom: 20px;
  backdrop-filter: blur(6px);
}
.auth-brand__title { font-size: 25px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 6px; }
.auth-brand__sub { font-size: 13px; color: rgba(255, 255, 255, 0.78); margin-bottom: 30px; }
.auth-brand__features { list-style: none; display: flex; flex-direction: column; gap: 15px; }
.auth-brand__features li {
  display: flex; align-items: center; gap: 11px;
  font-size: 13.5px; color: rgba(255, 255, 255, 0.93);
}
.dot {
  width: 30px; height: 30px; flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
}
.auth-deco {
  position: absolute;
  width: 230px; height: 230px;
  right: -40px; bottom: -30px;
  opacity: 0.75;
}

/* 右侧表单 */
.auth-form-wrap { padding: 44px 42px; display: flex; flex-direction: column; justify-content: center; }

.auth-head { display: flex; align-items: center; gap: 13px; margin-bottom: 24px; }
.auth-head__logo {
  display: none;
  width: 44px; height: 44px;
  border-radius: var(--radius-md);
  background: var(--gradient-brand);
  align-items: center; justify-content: center;
  font-size: 22px;
  box-shadow: var(--shadow-brand-sm);
}
.auth-head__title { font-size: 22px; font-weight: 800; letter-spacing: -0.02em; color: var(--text-primary); }
.auth-head__sub { font-size: 13px; color: var(--text-tertiary); margin-top: 2px; }

/* 分段控件 */
.auth-switch {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 4px;
  margin-bottom: 24px;
}
.auth-switch__btn {
  position: relative;
  z-index: 2;
  border: none; background: transparent; cursor: pointer;
  font-family: inherit; font-size: 14px; font-weight: 600;
  color: var(--text-tertiary);
  padding: 9px 0;
  border-radius: var(--radius-sm);
  transition: color var(--dur) var(--ease);
}
.auth-switch__btn.active { color: #fff; }
.auth-switch__thumb {
  position: absolute;
  z-index: 1;
  top: 4px; left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  border-radius: var(--radius-sm);
  background: var(--gradient-brand);
  box-shadow: var(--shadow-brand-sm);
  transition: transform 0.28s var(--ease-out);
}

.form-panel { animation: panelIn 0.32s var(--ease-out) both; }
@keyframes panelIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

:deep(.el-form-item__label) { padding-bottom: 4px; font-size: 13px; }

.auth-submit {
  width: 100%;
  height: 46px;
  margin-top: 6px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 3px;
  border: none;
  border-radius: var(--radius-md);
}

.auth-foot { text-align: center; margin-top: 18px; font-size: 13px; color: var(--text-tertiary); }
.auth-foot a { cursor: pointer; font-weight: 600; margin-left: 2px; }

@media (max-width: 860px) {
  .auth-shell { grid-template-columns: 1fr; max-width: 480px; }
  .auth-brand { display: none; }
  .auth-head__logo { display: flex; }
  .auth-form-wrap { padding: 34px 26px; }
}
@media (max-width: 420px) {
  .auth-page { padding: 14px; }
  .auth-form-wrap { padding: 28px 20px; }
  .auth-head__title { font-size: 19px; }
}
</style>
