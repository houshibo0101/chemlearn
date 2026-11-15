<template>
  <el-dialog
    :model-value="modelValue"
    :title="`从 PDF 截图 · 第 ${questionNo} 题`"
    width="min(1040px, 96vw)"
    top="3vh"
    :close-on-click-modal="false"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="crop-toolbar">
      <el-button-group>
        <el-button :disabled="page <= 1" @click="goPage(page - 1)">上一页</el-button>
        <el-button :disabled="page >= pageCount" @click="goPage(page + 1)">下一页</el-button>
      </el-button-group>
      <span class="crop-page">第 {{ page }} / {{ pageCount }} 页</span>
      <span class="crop-hint">在页面上按住拖动，框选需要给本题使用的图片 / 表格</span>
    </div>

    <div class="crop-viewport">
      <div
        ref="stage"
        class="crop-stage"
        v-loading="loading"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
        <img
          v-if="pageSrc"
          :src="pageSrc"
          alt="PDF 页面"
          draggable="false"
          @load="onImageLoad"
          @error="onImageError"
        />
        <div v-if="hasSelection" class="crop-selection" :style="selectionStyle">
          <span class="crop-size">{{ Math.round(sel.w * 100) }}% × {{ Math.round(sel.h * 100) }}%</span>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!hasSelection || loading" @click="save">
        保存截图
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  paperId: { type: [Number, String], default: null },
  questionNo: { type: [Number, String], default: null },
  initialPage: { type: Number, default: 1 },
  pageCount: { type: Number, default: 1 },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const page = ref(1)
const stage = ref(null)
const loading = ref(false)
const saving = ref(false)
const dragging = ref(false)
let dragStart = null
const sel = reactive({ x: 0, y: 0, w: 0, h: 0 })

const pageSrc = computed(() => (
  props.paperId
    ? `/chem/api/v1/papers/${props.paperId}/pageimg/${page.value}`
    : ''
))
const hasSelection = computed(() => sel.w > 0.01 && sel.h > 0.01)
const selectionStyle = computed(() => ({
  left: `${sel.x * 100}%`,
  top: `${sel.y * 100}%`,
  width: `${sel.w * 100}%`,
  height: `${sel.h * 100}%`,
}))

const resetSelection = () => {
  sel.x = 0; sel.y = 0; sel.w = 0; sel.h = 0
}

const goPage = (next) => {
  if (next < 1 || next > props.pageCount) return
  page.value = next
  loading.value = true
  resetSelection()
}

const onImageLoad = () => { loading.value = false }
const onImageError = () => {
  loading.value = false
  ElMessage.error('页面图加载失败，请检查这套卷是否已生成页面图')
}

const pointInStage = (event) => {
  const rect = stage.value.getBoundingClientRect()
  const clamp = (v) => Math.max(0, Math.min(1, v))
  return {
    x: clamp((event.clientX - rect.left) / rect.width),
    y: clamp((event.clientY - rect.top) / rect.height),
  }
}

const onPointerDown = (event) => {
  if (!stage.value || loading.value) return
  event.preventDefault()
  dragStart = pointInStage(event)
  dragging.value = true
  sel.x = dragStart.x
  sel.y = dragStart.y
  sel.w = 0
  sel.h = 0
  try { stage.value.setPointerCapture(event.pointerId) } catch {}
}

const onPointerMove = (event) => {
  if (!dragging.value || !dragStart) return
  event.preventDefault()
  const current = pointInStage(event)
  sel.x = Math.min(dragStart.x, current.x)
  sel.y = Math.min(dragStart.y, current.y)
  sel.w = Math.abs(current.x - dragStart.x)
  sel.h = Math.abs(current.y - dragStart.y)
}

const onPointerUp = (event) => {
  if (!dragging.value) return
  dragging.value = false
  try { stage.value?.releasePointerCapture(event.pointerId) } catch {}
}

const save = async () => {
  if (!hasSelection.value || !props.paperId || !props.questionNo) return
  saving.value = true
  try {
    const res = await api.post(
      `/papers/${props.paperId}/questions/${props.questionNo}/crop`,
      { page: page.value, x: sel.x, y: sel.y, w: sel.w, h: sel.h },
    )
    ElMessage.success('截图已保存，做题页配图已更新')
    emit('saved', res.figures || [])
    emit('update:modelValue', false)
  } catch {
    // 错误已由 api 拦截器提示
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (!visible) return
  page.value = Math.max(1, Math.min(props.pageCount || 1, props.initialPage || 1))
  loading.value = true
  resetSelection()
  // 同一张图重新打开时 <img> 不一定触发 load
  setTimeout(() => { loading.value = false }, 800)
})
</script>

<style scoped>
.crop-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.crop-page {
  font-size: 13px;
  color: var(--text-secondary);
}
.crop-hint {
  font-size: 12px;
  color: var(--text-placeholder);
}
.crop-viewport {
  max-height: 68vh;
  overflow: auto;
  background: #f8fafc;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.crop-stage {
  position: relative;
  width: 100%;
  user-select: none;
  touch-action: none;
  cursor: crosshair;
  line-height: 0;
  min-height: 180px;
}
.crop-stage img {
  display: block;
  width: 100%;
  height: auto;
  pointer-events: none;
}
.crop-selection {
  position: absolute;
  border: 2px solid #4f46e5;
  background: rgba(79, 70, 229, 0.16);
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.18);
  pointer-events: none;
}
.crop-size {
  position: absolute;
  right: 2px;
  bottom: 2px;
  background: #4f46e5;
  color: #fff;
  font-size: 10px;
  line-height: 1.4;
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap;
}
</style>
