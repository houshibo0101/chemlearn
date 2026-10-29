import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  { path: '/register', redirect: '/login' },
  { path: '/change-password', name: 'ChangePassword', component: () => import('@/views/ChangePassword.vue'), meta: { requiresAuth: true } },
  { path: '/', name: 'Home', component: () => import('@/views/Home.vue') },
  { path: '/practice', name: 'Practice', component: () => import('@/views/Practice.vue') },
  { path: '/papers', name: 'Papers', component: () => import('@/views/Papers.vue') },
  { path: '/practice/exam', name: 'PracticeExam', component: () => import('@/views/PracticeExam.vue') },
  { path: '/wrong', name: 'WrongQuestions', component: () => import('@/views/WrongQuestions.vue') },
  { path: '/favorites', name: 'Favorites', component: () => import('@/views/student/Favorites.vue') },
  { path: '/practice-history', name: 'PracticeHistory', component: () => import('@/views/student/PracticeHistory.vue') },
  { path: '/ai', name: 'AIChat', component: () => import('@/views/AIChat.vue') },
  { path: '/notifications', name: 'Notifications', component: () => import('@/views/Notifications.vue') },
  { path: '/report', name: 'LearningReport', component: () => import('@/views/LearningReport.vue') },
  { path: '/profile', name: 'Profile', component: () => import('@/views/Profile.vue') },
  { path: '/admin/questions', name: 'AdminQuestions', component: () => import('@/views/admin/QuestionManage.vue'), meta: { teacher: true } },
  { path: '/admin/users', name: 'AdminUsers', component: () => import('@/views/admin/UserManage.vue'), meta: { admin: true } },
  { path: '/admin/dashboard', name: 'AdminDashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { admin: true } },
  // 老师端
  { path: '/teacher/classes', name: 'TeacherClasses', component: () => import('@/views/teacher/ClassManage.vue'), meta: { teacher: true } },
  { path: '/teacher/assignments', name: 'TeacherAssignments', component: () => import('@/views/teacher/AssignmentManage.vue'), meta: { teacher: true } },
  { path: '/teacher/exams', name: 'TeacherExams', component: () => import('@/views/teacher/ExamManage.vue'), meta: { teacher: true } },
  { path: '/teacher/wrong-questions', name: 'TeacherWrong', component: () => import('@/views/teacher/StudentWrong.vue'), meta: { teacher: true } },
  // 学生端
  { path: '/student/assignments', name: 'StudentAssignments', component: () => import('@/views/student/Assignments.vue'), meta: { student: true } },
  { path: '/student/exams', name: 'StudentExams', component: () => import('@/views/student/Exams.vue'), meta: { student: true } },
  // 学习中心已移除，旧链接全部跳学习报告
  { path: '/learning/:page?', redirect: '/report' },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory('/chem/app/'),
  routes,
})

router.beforeEach((to, from, next) => {
  const store = useUserStore()
  // 已登录用户访问登录/注册页，跳转到首页
  if (to.meta.public && store.isLoggedIn) {
    next('/')
    return
  }
  // 公开页面直接放行
  if (to.meta.public) {
    next()
    return
  }
  // 未登录跳登录
  if (!store.isLoggedIn) {
    next('/login')
    return
  }
  // 管理员权限检查
  if (to.meta.admin && !store.isAdmin) {
    next('/')
    return
  }
  // 老师权限检查
  if (to.meta.teacher && store.user?.role !== 'teacher' && !store.isAdmin) {
    next('/')
    return
  }
  // 学生权限检查
  if (to.meta.student && store.user?.role !== 'student') {
    next('/')
    return
  }
  // 强制改密：如果用户标记了 must_change_password，且不是去改密页，就跳改密页
  if (store.user?.must_change_password && to.path !== '/change-password') {
    next('/change-password')
    return
  }
  // 已经改完密的，不允许再进改密页
  if (!store.user?.must_change_password && to.path === '/change-password') {
    next('/')
    return
  }
  next()
})

export default router
