<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2>🔑 API密钥管理</h2>
      <el-button type="primary" :icon="Plus" @click="openCreate">创建密钥</el-button>
    </div>

    <el-card class="page-card">
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">
        API Key 用于调用开放平台接口。请求时在 Header 中添加 <code>X-API-Key: 你的密钥</code>。
        接口文档：<el-link type="primary" href="/api/docs" target="_blank">查看 OpenAPI 文档</el-link>
      </p>
    </el-card>

    <el-card class="page-card" v-loading="loading">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="key" label="API Key" min-width="300">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:8px;">
              <code style="font-size:12px;background:var(--bg-tertiary);padding:2px 8px;border-radius:4px;word-break:break-all;">{{ row.key }}</code>
              <el-button text type="primary" size="small" @click="copyKey(row.key)">复制</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="call_count" label="调用次数" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag size="small" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="创建API密钥" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：我的小程序" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="create" :loading="saving">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const form = reactive({ name: '' })

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const loadList = async () => {
  loading.value = true
  try {
    list.value = await api.get('/api-keys')
  } finally {
    loading.value = false
  }
}

const openCreate = () => { form.name = ''; dialogVisible.value = true }

const create = async () => {
  if (!form.name.trim()) { ElMessage.warning('请输入名称'); return }
  saving.value = true
  try {
    await api.post('/api-keys', { name: form.name })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadList()
  } finally {
    saving.value = false
  }
}

const copyKey = (key) => {
  navigator.clipboard.writeText(key)
  ElMessage.success('已复制')
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除API密钥「${row.name}」？删除后无法恢复。`, '确认删除', { type: 'warning' })
    await api.delete(`/api-keys/${row.id}`)
    ElMessage.success('删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(loadList)
</script>
