<template>
  <div class="cp-page">
    <div class="cp-glow cp-glow--1"></div>
    <div class="cp-glow cp-glow--2"></div>

    <div class="cp-card">
      <div class="cp-icon">🔐</div>
      <h2 class="cp-title">首次登录</h2>
      <p class="cp-sub">为了账号安全，请修改初始密码</p>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item prop="old_password">
          <el-input v-model="form.old_password" type="password" size="large" placeholder="当前密码（初始密码 111111）" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="new_password">
          <el-input v-model="form.new_password" type="password" size="large" placeholder="新密码（至少 6 位）" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" size="large" placeholder="确认新密码" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="cp-submit" size="large" :loading="loading" @click="submit">确认修改</el-button>
        </el-form-item>
      </el-form>

      <div style="text-align:center;margin-top:6px;">
        <el-button text @click="logout">退出登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

const submit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await api.post('/auth/change-password', {
      old_password: form.old_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码修改成功')
    // 更新本地用户状态
    if (userStore.user) {
      userStore.user.must_change_password = false
      localStorage.setItem('user', JSON.stringify(userStore.user))
    }
    router.push('/')
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.cp-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: var(--bg-primary);
}
.cp-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: .55;
  pointer-events: none;
}
.cp-glow--1 { width: 420px; height: 420px; background: #C7D2FE; top: -150px; left: -110px; }
.cp-glow--2 { width: 360px; height: 360px; background: #A5F3FC; bottom: -140px; right: -80px; }
[data-theme='dark'] .cp-glow { opacity: .24; }

.cp-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: 40px 36px 32px;
  animation: cpIn .55s var(--ease-out) both;
}
@keyframes cpIn {
  from { opacity: 0; transform: translateY(20px) scale(.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.cp-icon {
  width: 62px; height: 62px;
  margin: 0 auto 16px;
  border-radius: var(--radius-lg);
  background: var(--gradient-brand);
  display: flex; align-items: center; justify-content: center;
  font-size: 30px;
  box-shadow: var(--shadow-brand);
}
.cp-title { text-align: center; font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }
.cp-sub { text-align: center; color: var(--text-tertiary); font-size: 13.5px; margin: 6px 0 26px; }
.cp-submit { width: 100%; height: 44px; font-size: 15px; font-weight: 700; letter-spacing: 2px; }

@media (max-width: 420px) {
  .cp-page { padding: 14px; }
  .cp-card { padding: 30px 22px 24px; }
}
</style>
