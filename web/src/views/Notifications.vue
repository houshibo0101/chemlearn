<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
      <h2>🔔 消息通知</h2>
      <el-button type="primary" plain size="small" :disabled="unread === 0" :loading="readAllLoading" @click="readAll">
        全部标为已读{{ unread > 0 ? `（${unread}条未读）` : '' }}
      </el-button>
    </div>

    <el-card v-if="list.length === 0 && !loading" class="page-card">
      <el-empty description="暂无消息" />
    </el-card>

    <el-card
      v-for="n in list"
      :key="n.id"
      class="page-card notif-card"
      :class="{ unread: !n.is_read }"
      @click="openItem(n)"
      style="cursor:pointer;"
    >
      <div style="display:flex;gap:12px;align-items:flex-start;">
        <div class="notif-icon" :class="'notif-icon--' + n.ntype">{{ iconOf(n.ntype) }}</div>
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:14.5px;font-weight:600;color:var(--text-primary);">{{ n.title }}</span>
            <span v-if="!n.is_read" class="notif-dot"></span>
          </div>
          <div v-if="n.content" style="font-size:13px;color:var(--text-secondary);margin-top:4px;line-height:1.6;">
            {{ n.content }}
          </div>
          <div style="font-size:12px;color:var(--text-placeholder);margin-top:6px;">{{ formatTime(n.created_at) }}</div>
        </div>
      </div>
    </el-card>

    <div v-if="list.length > 0" style="text-align:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, prev, pager, next"
        @current-change="loadList"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const list = ref([])
const total = ref(0)
const unread = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const readAllLoading = ref(false)

const iconOf = (t) => ({ assignment: '📝', exam: '📋', system: '📢' }[t] || '📢')

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const loadList = async () => {
  loading.value = true
  try {
    const res = await api.get('/notifications', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.items
    total.value = res.total
    unread.value = res.unread || 0
  } finally {
    loading.value = false
  }
}

const readAll = async () => {
  readAllLoading.value = true
  try {
    await api.post('/notifications/read-all')
    ElMessage.success('已全部标为已读')
    loadList()
  } finally {
    readAllLoading.value = false
  }
}

const openItem = async (n) => {
  if (!n.is_read) {
    try {
      await api.post(`/notifications/${n.id}/read`)
      n.is_read = true
      unread.value = Math.max(0, unread.value - 1)
    } catch {}
  }
  // 按类型跳转
  const role = userStore.user?.role
  if (n.ntype === 'assignment') {
    router.push(role === 'student' ? '/student/assignments' : role === 'teacher' ? '/teacher/assignments' : '/')
  } else if (n.ntype === 'exam') {
    router.push(role === 'student' ? '/student/exams' : role === 'teacher' ? '/teacher/exams' : '/')
  }
}

onMounted(loadList)
</script>

<style scoped>
.notif-card { transition: box-shadow .2s; }
.notif-card:hover { box-shadow: 0 4px 16px rgba(79, 70, 229, .10); }
.notif-card.unread { border-left: 3px solid var(--brand-600, #4F46E5); }
.notif-icon {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; background: var(--bg-tertiary);
}
.notif-icon--assignment { background: #EEF2FF; }
.notif-icon--exam { background: #FFFBEB; }
.notif-icon--system { background: #ECFDF5; }
.notif-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #EF4444; display: inline-block; flex-shrink: 0;
}
</style>
