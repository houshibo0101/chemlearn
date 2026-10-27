<template>
  <div class="app-container">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="margin:0;">👥 账号管理</h2>
      <div style="display:flex;gap:8px;">
        <el-button type="primary" :icon="Upload" @click="showImport = true">导入学生</el-button>
        <el-button :icon="Download" @click="downloadTemplate">下载模板</el-button>
      </div>
    </div>

    <!-- 系统统计面板 -->
    <el-row :gutter="16" style="margin-bottom:16px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align:center;">
            <div style="font-size:12px;color:var(--text-placeholder);margin-bottom:4px;">💾 服务器存储</div>
            <div style="font-size:24px;font-weight:bold;color:var(--brand-600);">{{ formatBytes(stats.storage?.total_bytes || 0) }}</div>
            <div style="font-size:12px;color:var(--text-placeholder);">/ 5GB ({{ stats.storage?.usage_percent || 0 }}%)</div>
            <el-progress :percentage="stats.storage?.usage_percent || 0" :color="storageColor" :stroke-width="8" style="margin-top:8px;" />
            <el-tag v-if="stats.storage?.is_full" type="danger" size="small" style="margin-top:4px;">存储已满！</el-tag>
            <el-tag v-else-if="stats.storage?.warning" type="warning" size="small" style="margin-top:4px;">存储即将满</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align:center;">
            <div style="font-size:12px;color:var(--text-placeholder);margin-bottom:4px;">🔑 AI Token消耗</div>
            <div style="font-size:24px;font-weight:bold;color:var(--success-color);">{{ (stats.token_usage?.total_tokens || 0).toLocaleString() }}</div>
            <div style="font-size:12px;color:var(--text-placeholder);">共 {{ stats.token_usage?.call_count || 0 }} 次调用</div>
            <div style="font-size:11px;color:var(--text-disabled);margin-top:6px;">
              输入 {{ (stats.token_usage?.prompt_tokens || 0).toLocaleString() }} · 输出 {{ (stats.token_usage?.completion_tokens || 0).toLocaleString() }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align:center;">
            <div style="font-size:12px;color:var(--text-placeholder);margin-bottom:4px;">👥 用户总数</div>
            <div style="font-size:24px;font-weight:bold;color:var(--warning-color);">{{ stats.users?.total || 0 }}</div>
            <div style="font-size:12px;color:var(--text-placeholder);">学生 {{ stats.users?.students || 0 }} · 管理员 {{ stats.users?.admins || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align:center;">
            <div style="font-size:12px;color:var(--text-placeholder);margin-bottom:4px;">📚 题库 / 错题</div>
            <div style="font-size:24px;font-weight:bold;color:var(--danger-color);">{{ stats.questions || 0 }}</div>
            <div style="font-size:12px;color:var(--text-placeholder);">题目 · 错题 {{ stats.wrong_questions || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <el-input v-model="keyword" placeholder="搜索用户名/姓名" clearable style="width:200px;" @keyup.enter="loadUsers" />
      <el-select v-model="roleFilter" placeholder="全部角色" clearable style="width:120px;" @change="loadUsers">
        <el-option label="学生" value="student" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-button type="primary" @click="loadUsers">搜索</el-button>
    </div>

    <!-- 用户列表 -->
    <el-table
      :data="tableData"
      stripe
      style="width:100%;"
      v-loading="loading"
      row-key="id"
      :tree-props="{ children: 'children' }"
      :expand-row-keys="expandedKeys"
      @expand-change="handleExpandChange"
    >
      <el-table-column type="expand" width="40">
        <template #default="{ row }">
          <div v-if="row.offline_children?.length" style="padding:0;">
            <div
              v-for="child in row.offline_children"
              :key="child.id"
              style="display:flex;align-items:center;padding:8px 20px;background:var(--accent-100);border-left:3px solid var(--brand-600);"
            >
              <span style="width:60px;color:var(--text-placeholder);">{{ child.id }}</span>
              <span style="width:140px;color:var(--text-secondary);">↳ {{ child.username }}</span>
              <span style="width:100px;">{{ child.full_name }}</span>
              <span style="width:80px;color:var(--text-placeholder);">{{ child.grade || '-' }}</span>
              <span style="width:120px;">
                <el-tag size="small" type="info">离线子账号</el-tag>
              </span>
              <span style="width:100px;">
                <el-tag :type="child.is_active ? 'success' : 'info'" size="small">
                  {{ child.is_active ? '正常' : '禁用' }}
                </el-tag>
              </span>
              <span style="color:var(--text-placeholder);font-size:12px;">绑定时间: {{ formatTime(child.bound_at) }}</span>
              <span style="margin-left:auto;">
                <el-button size="small" @click="resetPwd(child)">重置密码</el-button>
                <el-button size="small" type="info" @click="viewStats(row)">看主账号统计</el-button>
                <el-button size="small" type="warning" @click="unbindChild(row, child)">解绑</el-button>
              </span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="账号" width="160">
        <template #default="{ row }">
          <span>{{ row.username }}</span>
          <el-tag v-if="row.offline_child_count > 0" type="primary" size="small" style="margin-left:6px;">
            {{ row.offline_child_count }}个子账号
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="full_name" label="姓名" width="100" />
      <el-table-column prop="grade" label="学段" width="80" />
      <el-table-column label="班级" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.class_id" size="small" type="info">{{ getClassName(row.class_id) }}</el-tag>
          <span v-else style="color:var(--text-placeholder);">无班级</span>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-select
            v-model="row.role"
            size="small"
            :disabled="row.username === 'admin'"
            @change="changeRole(row)"
            style="width:100px;"
          >
            <el-option label="学生" value="student" />
            <el-option label="老师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="账号标签" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.tag === 'suspicious'" type="warning" size="small" effect="dark">数据异常</el-tag>
          <el-tag v-else-if="row.tag === 'banned'" type="danger" size="small" effect="dark">已封禁</el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="需改密" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.must_change_password" type="warning" size="small">是</el-tag>
          <span v-else style="color:var(--text-placeholder);">否</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="340" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="openChangeClass(row)" v-if="row.role === 'student'">转班</el-button>
          <el-button size="small" @click="resetPwd(row)" :disabled="row.role === 'admin' && row.username === 'admin'">重置密码</el-button>
          <el-button size="small" :type="row.tag === 'banned' ? 'success' : 'danger'" @click="banOrUnban(row)" :disabled="row.role === 'admin' && row.username === 'admin'">
            {{ row.tag === 'banned' ? '解封' : '封禁' }}
          </el-button>
          <el-button size="small" type="info" @click="viewStats(row)">统计</el-button>
          <el-button size="small" type="danger" @click="deleteUser(row)" :disabled="row.role === 'admin' && row.username === 'admin'">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="display:flex;justify-content:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadUsers"
        @current-change="loadUsers"
      />
    </div>

    <!-- 导入弹窗 -->
    <el-dialog v-model="showImport" title="批量导入学生" width="500px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px;">
        <p style="margin:0 0 4px;">Excel 需包含 <b>姓名</b> 列（必填），可选 <b>学段</b> 列（高一/高二/高三）和 <b>班级</b> 列（班级不存在会自动创建）。</p>
        <p style="margin:0;">账号自动生成姓名全拼，初始密码 <b>111111</b>，首次登录需修改密码。重名自动加数字后缀。</p>
      </el-alert>
      <el-upload
        drag
        action="#"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
        :on-remove="() => { importFile = null }"
      >
        <el-icon style="font-size:48px;color:var(--text-disabled);"><UploadFilled /></el-icon>
        <p>将 Excel 文件拖到此处，或<em>点击上传</em></p>
        <template #tip>
          <div style="color:var(--text-placeholder);font-size:12px;">支持 .xlsx / .xls 格式</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImport = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importFile" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 导入结果弹窗 -->
    <el-dialog v-model="showResult" title="导入结果" width="500px">
      <div style="margin-bottom:12px;">
        <el-tag type="success">成功 {{ importResult.success }}</el-tag>
        <el-tag type="danger" style="margin-left:8px;">失败 {{ importResult.failed }}</el-tag>
        <el-tag type="info" style="margin-left:8px;">总计 {{ importResult.total }}</el-tag>
      </div>
      <div style="max-height:300px;overflow-y:auto;background:var(--bg-tertiary);padding:10px;border-radius:6px;font-size:13px;line-height:1.8;">
        <div v-for="(d, i) in importResult.details" :key="i" :style="{ color: d.startsWith('✓') ? 'var(--success-color)' : 'var(--danger-color)' }">{{ d }}</div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showResult = false; loadUsers()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 转班弹窗 -->
    <el-dialog v-model="showChangeClass" title="转移班级" width="400px">
      <div style="margin-bottom:12px;">
        <p>学生：<b>{{ currentStudent?.full_name || currentStudent?.username }}</b></p>
        <p>当前班级：<b>{{ currentClassName || '无班级' }}</b></p>
      </div>
      <el-select v-model="targetClassId" placeholder="选择目标班级" style="width:100%;">
        <el-option label="移出班级（无班级）" :value="0" />
        <el-option v-for="c in classList" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <template #footer>
        <el-button @click="showChangeClass = false">取消</el-button>
        <el-button type="primary" :loading="changingClass" @click="doChangeClass">确认转班</el-button>
      </template>
    </el-dialog>

    <!-- API调用统计弹窗 -->
    <el-dialog v-model="statsDialog" title="API调用统计" width="500px">
      <div v-if="userStats">
        <p style="margin-bottom:16px;">用户：<b>{{ userStats.username }}</b></p>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="总调用次数">{{ userStats.total_calls }}</el-descriptions-item>
          <el-descriptions-item label="是否异常">
            <el-tag :type="userStats.is_anomaly ? 'warning' : 'success'" size="small">
              {{ userStats.is_anomaly ? '数据异常' : '正常' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="每分钟调用">{{ userStats.calls_per_minute }}</el-descriptions-item>
          <el-descriptions-item label="每小时调用">{{ userStats.calls_per_hour }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:16px;padding:12px;background:var(--bg-tertiary);border-radius:6px;font-size:13px;color:var(--text-secondary);">
          <p>📊 频率阈值：每分钟120次 / 每小时3000次 / 10秒内突发30次</p>
          <p style="margin-top:8px;">⚠️ 超过阈值会自动标记为"数据异常"，需管理员手动处理</p>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="statsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Download, UploadFilled } from '@element-plus/icons-vue'

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const roleFilter = ref('')
const loading = ref(false)
const expandedKeys = ref([])

// 表格数据（直接用users，offline_children在expand列里显示）
const tableData = computed(() => users.value)

const handleExpandChange = (row, expandedRows) => {
  if (expandedRows.includes(row)) {
    if (!expandedKeys.value.includes(row.id)) {
      expandedKeys.value.push(row.id)
    }
  } else {
    expandedKeys.value = expandedKeys.value.filter(id => id !== row.id)
  }
}

const unbindChild = async (parent, child) => {
  try {
    await ElMessageBox.confirm(`确定将子账号「${child.username}」从「${parent.username}」解绑吗？`, '确认解绑', { type: 'warning' })
    await api.delete(`/offline/unbind/${child.id}`)
    ElMessage.success('解绑成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('解绑失败：' + (e.response?.data?.detail || e.message))
  }
}
const showImport = ref(false)
const showResult = ref(false)
const importing = ref(false)
const importFile = ref(null)
const importResult = ref({ total: 0, success: 0, failed: 0, details: [] })
const stats = ref({ storage: {}, token_usage: {}, users: {}, questions: 0, wrong_questions: 0 })

// 转班相关
const showChangeClass = ref(false)
const changingClass = ref(false)
const currentStudent = ref(null)
const targetClassId = ref(null)
const classList = ref([])

const currentClassName = computed(() => {
  if (!currentStudent.value?.class_id) return ''
  const c = classList.value.find(c => c.id === currentStudent.value.class_id)
  return c?.name || ''
})

const getClassName = (classId) => {
  const c = classList.value.find(c => c.id === classId)
  return c?.name || '未知班级'
}

const loadClasses = async () => {
  try {
    const res = await api.get('/classes')
    classList.value = res.items || []
  } catch (e) {
    console.error('加载班级失败', e)
  }
}

const openChangeClass = (row) => {
  currentStudent.value = row
  targetClassId.value = row.class_id || 0
  showChangeClass.value = true
  if (classList.value.length === 0) loadClasses()
}

const doChangeClass = async () => {
  if (targetClassId.value === null) return ElMessage.warning('请选择目标班级')
  changingClass.value = true
  try {
    await api.put(`/admin/users/${currentStudent.value.id}/class?class_id=${targetClassId.value}`)
    ElMessage.success('转班成功')
    showChangeClass.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error('转班失败：' + (e.response?.data?.detail || e.message))
  } finally {
    changingClass.value = false
  }
}

const changeRole = async (row) => {
  try {
    await ElMessageBox.confirm(`确定将 ${row.full_name || row.username} 的角色改为${row.role === 'student' ? '学生' : row.role === 'teacher' ? '老师' : '管理员'}吗？`, '确认修改角色', { type: 'warning' })
    await api.put(`/admin/users/${row.id}/role?role=${row.role}`)
    ElMessage.success('角色修改成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('修改失败：' + (e.response?.data?.detail || e.message))
    }
    loadUsers()
  }
}

const banOrUnban = async (row) => {
  const action = row.tag === 'banned' ? '解封' : '封禁'
  try {
    await ElMessageBox.confirm(`确定${action}用户「${row.full_name || row.username}」吗？`, '确认', { type: 'warning' })
    if (row.tag === 'banned') {
      await api.post(`/admin/users/${row.id}/unban`)
    } else {
      await api.post(`/admin/users/${row.id}/ban`)
    }
    ElMessage.success(`${action}成功`)
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(`${action}失败：` + (e.response?.data?.detail || e.message))
  }
}

const statsDialog = ref(false)
const userStats = ref(null)
const viewStats = async (row) => {
  try {
    const res = await api.get(`/admin/users/${row.id}/api-stats`)
    userStats.value = res
    statsDialog.value = true
  } catch (e) {
    ElMessage.error('获取统计失败：' + (e.response?.data?.detail || e.message))
  }
}

const storageColor = computed(() => {
  const p = stats.value.storage?.usage_percent || 0
  if (p >= 100) return '#F56C6C'
  if (p >= 90) return '#E6A23C'
  return '#67C23A'
})

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const loadStats = async () => {
  try {
    const res = await api.get('/admin/users/stats/overview')
    stats.value = res
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

const loadUsers = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (roleFilter.value) params.role = roleFilter.value
    const res = await api.get('/admin/users', { params })
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const handleFileChange = (file) => {
  importFile.value = file.raw
}

const doImport = async () => {
  if (!importFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post('/admin/users/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importResult.value = res
    showImport.value = false
    showResult.value = true
    importFile.value = null
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    importing.value = false
  }
}

const downloadTemplate = () => {
  // 生成简单的CSV模板提示
  ElMessage.info('Excel模板：第一列表头"姓名"，第二列表头"学段"（可选）')
}

const resetPwd = async (row) => {
  try {
    await ElMessageBox.confirm(`确定将 ${row.full_name || row.username} 的密码重置为 111111 吗？`, '提示', { type: 'warning' })
    await api.post(`/admin/users/${row.id}/reset-password`)
    ElMessage.success('密码已重置为111111')
    loadUsers()
  } catch {}
}

const toggleUser = async (row) => {
  try {
    await api.post(`/admin/users/${row.id}/toggle`)
    ElMessage.success(row.is_active ? '已禁用' : '已启用')
    loadUsers()
  } catch {}
}

const deleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 ${row.full_name || row.username} 吗？此操作不可恢复！`, '警告', { type: 'error' })
    await api.delete(`/admin/users/${row.id}`)
    ElMessage.success('用户已删除')
    loadUsers()
  } catch {}
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => { loadUsers(); loadStats(); loadClasses() })
</script>
