<template>
  <div id="layout">
    <!-- 桌面端侧边栏 -->
    <div v-if="isDesktop && userStore.isLoggedIn && !isPublicPage" class="desktop-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand__logo">⚗️</div>
        <div>
          <div class="sidebar-brand__name">化学学习助手</div>
          <div class="sidebar-brand__sub">ChemLearn</div>
        </div>
      </div>
      <el-menu :default-active="route.path" router style="border:none;">
        <!-- 学生端菜单 -->
        <template v-if="userStore.user?.role === 'student'">
          <el-menu-item index="/"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
          <el-menu-item index="/practice"><el-icon><EditPen /></el-icon><span>刷题</span></el-menu-item>
          <el-menu-item index="/papers"><el-icon><Files /></el-icon><span>套卷练习</span></el-menu-item>
          <el-menu-item index="/wrong"><el-icon><Warning /></el-icon><span>错题本</span></el-menu-item>
          <el-menu-item index="/favorites"><el-icon><Star /></el-icon><span>我的收藏</span></el-menu-item>
          <el-menu-item index="/practice-history"><el-icon><History /></el-icon><span>做题历史</span></el-menu-item>
          <el-menu-item index="/ai"><el-icon><ChatDotRound /></el-icon><span>AI问答</span></el-menu-item>
          <el-menu-item index="/student/assignments"><el-icon><Document /></el-icon><span>我的作业</span></el-menu-item>
          <el-menu-item index="/student/exams"><el-icon><Tickets /></el-icon><span>我的考试</span></el-menu-item>
          <el-menu-item index="/report"><el-icon><DataLine /></el-icon><span>学习报告</span></el-menu-item>
        </template>
        <!-- 老师端菜单 -->
        <template v-else-if="userStore.user?.role === 'teacher'">
          <el-menu-item index="/ai"><el-icon><ChatDotRound /></el-icon><span>AI问答</span></el-menu-item>
          <el-menu-item index="/papers"><el-icon><Files /></el-icon><span>套卷练习</span></el-menu-item>
          <el-menu-item index="/teacher/classes"><el-icon><School /></el-icon><span>班级管理</span></el-menu-item>
          <el-menu-item index="/teacher/assignments"><el-icon><Document /></el-icon><span>作业管理</span></el-menu-item>
          <el-menu-item index="/teacher/exams"><el-icon><Tickets /></el-icon><span>考试管理</span></el-menu-item>
          <el-menu-item index="/teacher/wrong-questions"><el-icon><Warning /></el-icon><span>学生错题</span></el-menu-item>
          <el-menu-item index="/admin/questions"><el-icon><Upload /></el-icon><span>题目上传</span></el-menu-item>
          <el-menu-item index="/report"><el-icon><DataLine /></el-icon><span>学习报告</span></el-menu-item>
        </template>
        <!-- 管理员菜单 -->
        <template v-else>
          <el-menu-item index="/"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
          <el-menu-item index="/practice"><el-icon><EditPen /></el-icon><span>刷题</span></el-menu-item>
          <el-menu-item index="/papers"><el-icon><Files /></el-icon><span>套卷练习</span></el-menu-item>
          <el-menu-item index="/wrong"><el-icon><Warning /></el-icon><span>错题本</span></el-menu-item>
          <el-menu-item index="/ai"><el-icon><ChatDotRound /></el-icon><span>AI问答</span></el-menu-item>
          <el-menu-item index="/teacher/classes"><el-icon><School /></el-icon><span>班级管理</span></el-menu-item>
          <el-menu-item index="/admin/questions"><el-icon><Setting /></el-icon><span>题库管理</span></el-menu-item>
          <el-menu-item index="/admin/users"><el-icon><UserFilled /></el-icon><span>账号管理</span></el-menu-item>
          <el-menu-item index="/report"><el-icon><DataLine /></el-icon><span>学习报告</span></el-menu-item>
        </template>
        <el-menu-item index="/notifications">
          <el-icon><Bell /></el-icon>
          <span>消息通知</span>
          <el-badge v-if="unreadCount > 0" :value="unreadCount" :max="99" style="margin-left:8px;" />
        </el-menu-item>
        <el-menu-item index="/profile"><el-icon><User /></el-icon><span>个人中心</span></el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <div style="display:flex;gap:8px;margin-bottom:10px;">
          <el-button plain size="small" style="flex:1;" @click="toggleDark">
            <el-icon><component :is="isDark ? 'Sunny' : 'Moon'" /></el-icon>
            {{ isDark ? '亮色模式' : '暗色模式' }}
          </el-button>
        </div>
        <el-button type="danger" plain size="small" style="width:100%;" @click="logout">退出登录</el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div :class="isDesktop && userStore.isLoggedIn && !isPublicPage ? 'desktop-main' : ''" style="min-height:100vh;">
      <!-- 手机端顶部栏 -->
      <div v-if="!isDesktop && userStore.isLoggedIn && !isPublicPage" class="mobile-topbar">
        <div style="display:flex;align-items:center;gap:9px;">
          <div class="mobile-topbar__logo">⚗️</div>
          <span style="font-weight:700;font-size:15px;color:var(--text-primary);">化学学习助手</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
            <el-button text size="small" @click="$router.push('/notifications')" style="color:var(--text-secondary);padding:4px;">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-button text size="small" @click="toggleDark" style="color:var(--text-secondary);padding:4px;">
            <el-icon :size="18"><component :is="isDark ? 'Sunny' : 'Moon'" /></el-icon>
          </el-button>
          <el-dropdown @command="handleCmd">
            <span style="cursor:pointer;display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-secondary);font-weight:600;">
              <el-avatar :size="27" style="background:var(--gradient-brand);font-size:12px;">{{ userStore.user?.full_name?.[0] || userStore.user?.username?.[0] }}</el-avatar>
              {{ userStore.user?.full_name || userStore.user?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <router-view />

      <!-- 手机端底部导航 -->
      <div v-if="!isDesktop && userStore.isLoggedIn && !isPublicPage" class="mobile-tabbar">
        <!-- 学生端 -->
        <template v-if="userStore.user?.role === 'student'">
          <div class="mobile-tabbar-item" :class="{active: route.path==='/'}" @click="$router.push('/')">
            <el-icon><HomeFilled /></el-icon><span>首页</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/practice'}" @click="$router.push('/practice')">
            <el-icon><EditPen /></el-icon><span>刷题</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/student/assignments'}" @click="$router.push('/student/assignments')">
            <el-icon><Document /></el-icon><span>作业</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/student/exams'}" @click="$router.push('/student/exams')">
            <el-icon><Tickets /></el-icon><span>考试</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/profile'}" @click="$router.push('/profile')">
            <el-icon><User /></el-icon><span>我的</span>
          </div>
        </template>
        <!-- 老师端 -->
        <template v-else-if="userStore.user?.role === 'teacher'">
          <div class="mobile-tabbar-item" :class="{active: route.path==='/ai'}" @click="$router.push('/ai')">
            <el-icon><ChatDotRound /></el-icon><span>AI</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/teacher/classes'}" @click="$router.push('/teacher/classes')">
            <el-icon><School /></el-icon><span>班级</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/teacher/assignments'}" @click="$router.push('/teacher/assignments')">
            <el-icon><Document /></el-icon><span>作业</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/teacher/exams'}" @click="$router.push('/teacher/exams')">
            <el-icon><Tickets /></el-icon><span>考试</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/profile'}" @click="$router.push('/profile')">
            <el-icon><User /></el-icon><span>我的</span>
          </div>
        </template>
        <!-- 管理员端 -->
        <template v-else>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/'}" @click="$router.push('/')">
            <el-icon><HomeFilled /></el-icon><span>首页</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/practice'}" @click="$router.push('/practice')">
            <el-icon><EditPen /></el-icon><span>刷题</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/admin/questions'}" @click="$router.push('/admin/questions')">
            <el-icon><Upload /></el-icon><span>题库</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/admin/users'}" @click="$router.push('/admin/users')">
            <el-icon><UserFilled /></el-icon><span>用户</span>
          </div>
          <div class="mobile-tabbar-item" :class="{active: route.path==='/profile'}" @click="$router.push('/profile')">
            <el-icon><User /></el-icon><span>我的</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'
import { DataLine, Moon, Sunny, Bell } from '@element-plus/icons-vue'
import { getTheme, toggleTheme as doToggleTheme } from '@/utils/theme'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isDesktop = ref(window.innerWidth >= 768)
const isPublicPage = computed(() => route.path === '/login' || route.path === '/register')
const isDark = ref(getTheme() === 'dark')

// ===== 未读通知轮询 =====
const unreadCount = ref(0)
let notifTimer = null
const fetchUnread = async () => {
  if (!userStore.isLoggedIn) { unreadCount.value = 0; return }
  try {
    const res = await api.get('/notifications/unread-count')
    unreadCount.value = res.count || 0
  } catch {}
}
onMounted(() => {
  fetchUnread()
  notifTimer = setInterval(fetchUnread, 60000)
})
onUnmounted(() => { if (notifTimer) clearInterval(notifTimer) })
watch(() => route.path, fetchUnread)

const checkWidth = () => { isDesktop.value = window.innerWidth >= 768 }
onMounted(() => window.addEventListener('resize', checkWidth))
onUnmounted(() => window.removeEventListener('resize', checkWidth))

const toggleDark = () => {
  doToggleTheme()
  isDark.value = !isDark.value
}

const handleCmd = (cmd) => {
  if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'logout') logout()
}

const logout = async () => {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  } catch {}
}
</script>
