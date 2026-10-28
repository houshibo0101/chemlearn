<template>
  <div class="auth-page">
    <div class="auth-shell">
      <!-- 左侧说明区 -->
      <aside class="auth-side">
        <div class="auth-side__top">
          <div class="auth-mark">⚗️</div>
          <div>
            <div class="auth-mark__name">化学学习助手</div>
            <div class="auth-mark__sub">ChemLearn</div>
          </div>
        </div>

        <h1 class="auth-side__title">让化学学习<br />有章法地推进</h1>
        <p class="auth-side__desc">从第一道题开始记录，薄弱点在数据里自己会说话。</p>

        <ol class="auth-points">
          <li v-for="(p, i) in points" :key="p.title">
            <span class="auth-points__no">{{ String(i + 1).padStart(2, '0') }}</span>
            <div>
              <div class="auth-points__title">{{ p.title }}</div>
              <div class="auth-points__desc">{{ p.desc }}</div>
            </div>
          </li>
        </ol>

        <div class="auth-side__foot">高考真题题库 · 智能推题 · 学习报告</div>
      </aside>

      <!-- 右侧表单区 -->
      <section class="auth-form-wrap">
        <header class="auth-head">
          <div class="auth-head__title">
            {{ activeTab === 'login' ? '登录' : '创建账号' }}
          </div>
          <div class="auth-head__sub">
            {{ activeTab === 'login' ? '继续你的学习进度' : '填写信息，立刻开始' }}
          </div>
        </header>

        <!-- 分段切换 -->
        <div class="auth-switch" :data-tab="activeTab">
          <button
            class="auth-switch__btn"
            :class="{ active: activeTab === 'login' }"
            @click="switchTab('login')"
          >登录</button>
          <button
            class="auth-switch__btn"
            :class="{ active: activeTab === 'register' }"
            @click="switchTab('register')"
          >注册</button>
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
          <div class="auth-foot">
            还没有账号？<a @click="switchTab('register')">立即注册</a>
          </div>
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
            <div class="auth-grid">
              <el-form-item label="姓名">
                <el-input v-model="registerForm.full_name" size="large" placeholder="用于错题导出" :prefix-icon="Postcard" />
              </el-form-item>
              <el-form-item label="学段">
                <el-select v-model="registerForm.grade" size="large" placeholder="选择学段" style="width:100%;">
                  <el-option label="高一" value="高一" />
                  <el-option label="高二" value="高二" />
                  <el-option label="高三" value="高三" />
                </el-select>
              </el-form-item>
            </div>
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

const points = [
  { title: '完整题库', desc: '高考真题与知识点分类练习' },
  { title: '智能推题', desc: '按薄弱知识点持续推题' },
  { title: '错题本', desc: '自动归集，支持批量导出' },
  { title: '学习报告', desc: '正确率、进度与掌握情况' },
]

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
  padding: 28px;
  background: var(--bg-primary);
  background-image: radial-gradient(var(--border-color) 1px, transparent 1px);
  background-size: 22px 22px;
  background-position: -1px -1px;
}

.auth-shell {
  width: 100%;
  max-width: 900px;
  display: grid;
  grid-template-columns: 0.86fr 1.14fr;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: shellIn 0.34s var(--ease-out) both;
}
@keyframes shellIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 左侧说明区：中性底色 + 品牌色点缀，不用大面积渐变 */
.auth-side {
  background: var(--bg-tertiary);
  border-right: 1px solid var(--border-light);
  padding: 38px 34px;
  display: flex;
  flex-direction: column;
}
.auth-side__top { display: flex; align-items: center; gap: 11px; margin-bottom: 30px; }
.auth-mark {
  width: 40px; height: 40px;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.auth-mark__name { font-size: 14px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em; }
.auth-mark__sub {
  font-size: 11px;
  color: var(--text-placeholder);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 1px;
}

.auth-side__title {
  font-size: 24px;
  line-height: 1.42;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 10px;
}
.auth-side__desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-tertiary);
  margin: 0 0 26px;
}

.auth-points { list-style: none; margin: 0; padding: 0; flex: 1; }
.auth-points li {
  display: flex;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px dashed var(--border-light);
}
.auth-points li:first-child { padding-top: 0; }
.auth-points li:last-child { border-bottom: none; }
.auth-points__no {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--brand-400);
  padding-top: 2px;
  flex-shrink: 0;
}
.auth-points__title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.auth-points__desc { font-size: 12px; color: var(--text-placeholder); margin-top: 2px; line-height: 1.55; }

.auth-side__foot {
  margin-top: 24px;
  font-size: 11.5px;
  color: var(--text-disabled);
  letter-spacing: 0.01em;
}

/* 右侧表单 */
.auth-form-wrap {
  padding: 40px 40px 34px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-head { margin-bottom: 22px; }
.auth-head__title { font-size: 21px; font-weight: 700; letter-spacing: -0.02em; color: var(--text-primary); }
.auth-head__sub { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

/* 分段控件：实心品牌色滑块 */
.auth-switch {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 3px;
  margin-bottom: 22px;
}
.auth-switch__btn {
  position: relative;
  z-index: 2;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-tertiary);
  padding: 8px 0;
  border-radius: var(--radius-sm);
  transition: color var(--dur) var(--ease);
}
.auth-switch__btn.active { color: #fff; }
.auth-switch::after {
  content: '';
  position: absolute;
  z-index: 1;
  top: 3px; left: 3px;
  width: calc(50% - 3px);
  height: calc(100% - 6px);
  border-radius: var(--radius-sm);
  background: var(--brand-600);
  transition: transform 0.24s var(--ease-out);
}
.auth-switch[data-tab='register']::after { transform: translateX(100%); }

.form-panel { animation: panelIn 0.24s var(--ease-out) both; }
@keyframes panelIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.auth-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

:deep(.el-form-item) { margin-bottom: 16px; }
:deep(.el-form-item__label) {
  padding-bottom: 5px;
  font-size: 12.5px;
  color: var(--text-secondary);
  font-weight: 500;
}

.auth-submit {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 4px;
  border: none;
  border-radius: var(--radius-md);
  box-shadow: none;
}

.auth-foot {
  text-align: center;
  margin-top: 16px;
  font-size: 12.5px;
  color: var(--text-tertiary);
}
.auth-foot a { cursor: pointer; font-weight: 600; margin-left: 2px; color: var(--brand-600); }
.auth-foot a:hover { color: var(--brand-700); }

@media (max-width: 860px) {
  .auth-shell { grid-template-columns: 1fr; max-width: 460px; }
  .auth-side { display: none; }
  .auth-form-wrap { padding: 32px 26px; }
}
@media (max-width: 420px) {
  .auth-page { padding: 14px; }
  .auth-form-wrap { padding: 26px 20px; }
  .auth-grid { grid-template-columns: 1fr; gap: 0; }
}
</style>
