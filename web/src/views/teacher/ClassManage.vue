<template>
  <div class="class-manage">
    <div class="page-header">
      <h2>班级管理</h2>
      <div>
        <el-button @click="showJoin = true" v-if="userStore.user?.role !== 'student'">加入班级</el-button>
        <el-button type="primary" @click="showCreate = true" v-if="userStore.user?.role !== 'student'" style="margin-left:8px;">+ 新建班级</el-button>
      </div>
    </div>

    <el-table :data="classes" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="班级名称" />
      <el-table-column prop="grade" label="学段" width="120" />
      <el-table-column prop="student_count" label="学生数" width="100" />
      <el-table-column label="邀请码" width="140">
        <template #default="{ row }">
          <span v-if="row.join_code" style="font-family:monospace;font-weight:bold;letter-spacing:2px;">{{ row.join_code }}</span>
          <el-button v-if="row.join_code" link type="primary" size="small" @click="copyCode(row.join_code)">复制</el-button>
          <el-button v-if="row.join_code" link type="warning" size="small" @click="regenCode(row)">重置</el-button>
          <span v-else style="color:var(--text-placeholder);">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="viewStudents(row)">学生</el-button>
          <el-button size="small" @click="viewStats(row)">统计</el-button>
          <el-button size="small" type="danger" @click="deleteClass(row)" v-if="userStore.isAdmin">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建班级弹窗 -->
    <el-dialog v-model="showCreate" title="新建班级" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="班级名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="学段">
          <el-select v-model="form.grade" placeholder="请选择">
            <el-option label="高一" value="高一" />
            <el-option label="高二" value="高二" />
            <el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createClass">创建</el-button>
      </template>
    </el-dialog>

    <!-- 加入班级弹窗 -->
    <el-dialog v-model="showJoin" title="加入班级" width="400px">
      <el-form label-width="80px">
        <el-form-item label="邀请码">
          <el-input v-model="joinCode" placeholder="请输入6位邀请码" maxlength="6" style="text-transform:uppercase;letter-spacing:4px;font-family:monospace;" />
        </el-form-item>
        <div style="color:var(--text-placeholder);font-size:13px;margin-top:-10px;margin-bottom:10px;">
          向班级管理员或已有老师索取邀请码
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showJoin = false">取消</el-button>
        <el-button type="primary" @click="joinClass" :loading="joining">加入</el-button>
      </template>
    </el-dialog>

    <!-- 学生列表弹窗 -->
    <el-dialog v-model="showStudents" :title="`${currentClass?.name || ''} - 学生列表`" width="600px">
      <el-table :data="students" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="full_name" label="姓名" />
        <el-table-column prop="grade" label="学段" width="100" />
      </el-table>
    </el-dialog>

    <!-- 班级统计弹窗 -->
    <el-dialog v-model="showStatsDialog" :title="`${currentClass?.name || ''} - 学习统计`" width="700px">
      <div v-if="stats" class="stats-summary">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="学生总数">{{ stats.student_total }}</el-descriptions-item>
          <el-descriptions-item label="错题总数">{{ stats.total_wrong_questions }}</el-descriptions-item>
          <el-descriptions-item label="人均错题">{{ stats.avg_wrong_per_student }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="stats.students" stripe style="margin-top:16px">
          <el-table-column prop="name" label="学生" />
          <el-table-column prop="wrong_count" label="错题数" width="120" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="viewWrongQuestions(row.student_id)">查看错题</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const classes = ref([])
const students = ref([])
const stats = ref(null)
const showCreate = ref(false)
const showJoin = ref(false)
const showStudents = ref(false)
const showStatsDialog = ref(false)
const currentClass = ref(null)
const form = ref({ name: '', grade: '', description: '' })
const joinCode = ref('')
const joining = ref(false)

async function loadClasses() {
  const res = await api.get('/classes')
  classes.value = res.items || []
}

async function createClass() {
  if (!form.value.name) return ElMessage.warning('请输入班级名称')
  await api.post('/classes', form.value)
  ElMessage.success('创建成功')
  showCreate.value = false
  form.value = { name: '', grade: '', description: '' }
  loadClasses()
}

async function joinClass() {
  if (!joinCode.value || joinCode.value.length !== 6) {
    return ElMessage.warning('请输入6位邀请码')
  }
  joining.value = true
  try {
    const res = await api.post('/classes/join', { join_code: joinCode.value.toUpperCase() })
    ElMessage.success(res.message || '加入成功')
    showJoin.value = false
    joinCode.value = ''
    loadClasses()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加入失败')
  } finally {
    joining.value = false
  }
}

function copyCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    ElMessage.success('邀请码已复制')
  }).catch(() => {
    ElMessage.warning('复制失败，请手动复制')
  })
}

async function regenCode(row) {
  try {
    await ElMessageBox.confirm(`确定重置班级「${row.name}」的邀请码？旧邀请码将失效。`, '提示', { type: 'warning' })
    const res = await api.post(`/classes/${row.id}/regenerate-code`)
    row.join_code = res.join_code
    ElMessage.success('邀请码已重置')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '重置失败')
  }
}

async function deleteClass(row) {
  try {
    await ElMessageBox.confirm(`确定删除班级「${row.name}」？删除后该班级的学生将变为无班级状态。`, '提示', { type: 'warning' })
    await api.delete(`/classes/${row.id}`)
    ElMessage.success('删除成功')
    loadClasses()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

async function viewStudents(row) {
  currentClass.value = row
  const res = await api.get(`/classes/${row.id}/students`)
  students.value = res.items || []
  showStudents.value = true
}

async function viewStats(row) {
  currentClass.value = row
  const res = await api.get(`/teacher/classes/${row.id}/stats`)
  stats.value = res
  showStatsDialog.value = true
}

async function viewWrongQuestions(studentId) {
  // 跳转到学生错题详情
  window.location.href = `/app/teacher/wrong-questions?class_id=${currentClass.value.id}&student_id=${studentId}`
}

onMounted(loadClasses)
</script>

<style scoped>
.class-manage { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.stats-summary { margin-top: 10px; }
</style>
