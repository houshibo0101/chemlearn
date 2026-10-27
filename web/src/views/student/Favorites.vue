<template>
  <div class="app-container" style="padding-bottom:80px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
      <h2>⭐ 我的收藏</h2>
      <el-button v-if="favorites.length > 0" type="primary" size="small" @click="startPractice">
        <el-icon><EditPen /></el-icon>批量练习
      </el-button>
    </div>

    <!-- 筛选 -->
    <el-card class="page-card" style="margin-bottom:12px;">
      <el-form :inline="true" size="small">
        <el-form-item label="知识点">
          <el-select v-model="filterKP" placeholder="全部" clearable style="width:160px;" @change="loadFavorites">
            <el-option v-for="kp in knowledgePoints" :key="kp" :label="kp" :value="kp" />
          </el-select>
        </el-form-item>
        <el-form-item label="题型">
          <el-select v-model="filterType" placeholder="全部" clearable style="width:120px;" @change="loadFavorites">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multiple" />
            <el-option label="填空" value="fill" />
            <el-option label="计算" value="calculation" />
            <el-option label="简答" value="subjective" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-empty v-if="loading === false && favorites.length === 0" description="还没有收藏的题目" />

    <div v-for="item in filteredFavorites" :key="item.id" class="fav-card">
      <el-card class="page-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div style="flex:1;min-width:0;">
            <div style="margin-bottom:8px;">
              <el-tag size="small" :type="typeColor(item.question_type)">{{ typeText(item.question_type) }}</el-tag>
              <el-tag size="small" :type="diffColor(item.difficulty)" style="margin-left:6px;">{{ diffText(item.difficulty) }}</el-tag>
              <span v-if="item.knowledge_point" style="margin-left:8px;font-size:12px;color:var(--text-placeholder);">{{ item.knowledge_point }}</span>
            </div>
            <div style="font-weight:600;font-size:15px;line-height:1.6;color:var(--text-primary);">{{ item.title }}</div>
            <div v-if="item.content" style="font-size:13px;color:var(--text-secondary);margin-top:6px;white-space:pre-wrap;line-height:1.6;">{{ item.content }}</div>
          </div>
          <el-button text type="danger" size="small" @click="removeFav(item.question_id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </el-card>
    </div>

    <div v-if="total > pageSize" style="text-align:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadFavorites"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const favorites = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filterKP = ref('')
const filterType = ref('')
const knowledgePoints = ref([])

const filteredFavorites = computed(() => {
  let list = favorites.value
  if (filterType.value) list = list.filter(f => f.question_type === filterType.value)
  return list
})

const typeText = (t) => ({ single: '单选', multiple: '多选', fill: '填空', calculation: '计算', subjective: '简答' }[t] || t)
const typeColor = (t) => ({ single: '', multiple: 'success', fill: 'warning', calculation: 'danger', subjective: 'info' }[t] || '')
const diffText = (d) => ({ easy: '简单', medium: '中等', hard: '困难' }[d] || d)
const diffColor = (d) => ({ easy: 'success', medium: 'warning', hard: 'danger' }[d] || '')

const loadFavorites = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filterKP.value) params.knowledge_point = filterKP.value
    const res = await api.get('/favorites', { params })
    favorites.value = res.items
    total.value = res.total
    // 收集知识点
    const kps = new Set()
    res.items.forEach(f => { if (f.knowledge_point) kps.add(f.knowledge_point) })
    knowledgePoints.value = Array.from(kps)
  } finally {
    loading.value = false
  }
}

const removeFav = async (qid) => {
  try {
    await ElMessageBox.confirm('确定取消收藏这道题吗？', '提示', { type: 'warning' })
    await api.delete(`/favorites/${qid}`)
    ElMessage.success('已取消收藏')
    loadFavorites()
  } catch {}
}

const startPractice = () => {
  const ids = filteredFavorites.value.map(f => f.question_id)
  sessionStorage.setItem('practice_favorites', JSON.stringify(ids))
  router.push('/practice/exam')
}

onMounted(loadFavorites)
</script>

<style scoped>
.fav-card { margin-bottom: 12px; }
</style>
