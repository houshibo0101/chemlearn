<template>
  <el-dialog
    v-model="visible"
    title="晶胞结构编辑器"
    width="92%"
    top="3vh"
    :close-on-click-modal="false"
    class="crystal-dialog"
  >
    <div class="crystal-wrap">
      <div class="crystal-toolbar">
        <el-select v-model="templateKey" style="width: 150px;" @change="applyTemplate">
          <el-option label="简单立方" value="sc" />
          <el-option label="体心立方" value="bcc" />
          <el-option label="面心立方" value="fcc" />
          <el-option label="NaCl 型" value="nacl" />
          <el-option label="CsCl 型" value="cscl" />
          <el-option label="金刚石型" value="diamond" />
        </el-select>
        <el-button :icon="Refresh" @click="applyTemplate">重置模板</el-button>
        <span class="crystal-toolbar__label">点击原子设为：</span>
        <el-radio-group v-model="brush" size="small">
          <el-radio-button value="A">A</el-radio-button>
          <el-radio-button value="B">B</el-radio-button>
          <el-radio-button value="off">隐藏</el-radio-button>
        </el-radio-group>
        <el-checkbox v-model="showLabels">显示 A/B 标签</el-checkbox>
        <el-checkbox v-model="addMode">点空白添加原子</el-checkbox>
        <el-button :icon="Delete" @click="clearAtoms">清空原子</el-button>
      </div>

      <div class="crystal-main">
        <div class="crystal-canvas" :class="{ 'crystal-canvas--add': addMode }">
          <svg ref="svgRef" :viewBox="`0 0 ${W} ${H}`" xmlns="http://www.w3.org/2000/svg" @click="onCanvasClick">
            <rect :width="W" :height="H" fill="#ffffff" />
            <g class="crystal-edges">
              <line
                v-for="(edge, i) in edges"
                :key="'e' + i"
                :x1="edge[0]" :y1="edge[1]" :x2="edge[2]" :y2="edge[3]"
                stroke="#94a3b8" stroke-width="2"
              />
            </g>
            <g class="crystal-atoms">
              <g
                v-for="(atom, i) in visibleAtoms"
                :key="atom.id || i"
                class="crystal-atom"
                @click.stop="onAtomClick(atom)"
              >
                <circle
                  :cx="atom.x" :cy="atom.y" :r="radius"
                  :fill="colorOf(atom.kind)"
                  stroke="#0f172a" stroke-width="1.6"
                />
                <text
                  v-if="showLabels"
                  :x="atom.x" :y="atom.y + 4"
                  text-anchor="middle"
                  :fill="atom.kind === 'A' ? '#ffffff' : '#1f2937'"
                  font-size="11" font-weight="600"
                  font-family="Microsoft YaHei, Arial, sans-serif"
                >{{ atom.kind }}</text>
              </g>
            </g>
          </svg>
          <div class="crystal-canvas__hint">点击原子可切换 A / B / 隐藏；开启“点空白添加原子”后可补充自定义位置</div>
        </div>

        <div class="crystal-side">
          <div class="crystal-side__title">晶胞信息</div>
          <div class="crystal-stat">
            <span>模板</span><b>{{ templateName }}</b>
          </div>
          <div class="crystal-stat">
            <span>A 原子</span><b>{{ countOf('A') }}</b>
          </div>
          <div class="crystal-stat">
            <span>B 原子</span><b>{{ countOf('B') }}</b>
          </div>
          <div class="crystal-legend">
            <div><i class="dot dot--a" /> A 原子</div>
            <div><i class="dot dot--b" /> B 原子</div>
          </div>
          <div class="crystal-tip">
            <p>适合高中结构化学的晶胞投影图：棱、顶点、面心、体心、棱心都可以编辑。</p>
            <p>画完点「插入到题目」，会作为题目图片保存，做题页和题目预览都会显示。</p>
          </div>
        </div>
      </div>

      <div class="crystal-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="insertToQuestion">插入到题目</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'insert'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const W = 640
const H = 480
const svgRef = ref(null)
const templateKey = ref('sc')
const brush = ref('A')
const showLabels = ref(true)
const addMode = ref(false)
const radius = 11
const exporting = ref(false)
const atoms = ref([])

const front = [[120, 180], [440, 180], [440, 430], [120, 430]]
const back = [[190, 110], [510, 110], [510, 360], [190, 360]]
const cubeCenter = [305, 270]
const faceCenters = [
  [280, 305], // 前面
  [350, 235], // 后面
  [155, 270], // 左面
  [475, 270], // 右面
  [305, 145], // 上面
  [305, 395], // 下面
]
const cornerPoints = [...front, ...back]
const edgePairs = [
  [0, 1], [1, 2], [2, 3], [3, 0],
  [4, 5], [5, 6], [6, 7], [7, 4],
  [0, 4], [1, 5], [2, 6], [3, 7],
]
const edges = edgePairs.map(([a, b]) => [
  cornerPoints[a][0], cornerPoints[a][1], cornerPoints[b][0], cornerPoints[b][1],
])
const edgeCenters = edgePairs.map(([a, b]) => [
  (cornerPoints[a][0] + cornerPoints[b][0]) / 2,
  (cornerPoints[a][1] + cornerPoints[b][1]) / 2,
])

const templateName = computed(() => ({
  sc: '简单立方',
  bcc: '体心立方',
  fcc: '面心立方',
  nacl: 'NaCl 型',
  cscl: 'CsCl 型',
  diamond: '金刚石型',
}[templateKey.value] || '自定义'))

const visibleAtoms = computed(() => atoms.value.filter((a) => a.kind !== 'off'))

const colorOf = (kind) => (kind === 'A' ? '#334155' : '#fbbf24')
const countOf = (kind) => atoms.value.filter((a) => a.kind === kind).length

let seq = 0
const makeAtom = (point, kind = 'A') => ({ id: ++seq, x: point[0], y: point[1], kind })

const applyTemplate = () => {
  const list = cornerPoints.map((p) => makeAtom(p, 'A'))
  if (templateKey.value === 'bcc' || templateKey.value === 'cscl') {
    list.push(makeAtom(cubeCenter, 'B'))
  } else if (templateKey.value === 'fcc') {
    faceCenters.forEach((p) => list.push(makeAtom(p, 'A')))
  } else if (templateKey.value === 'nacl') {
    faceCenters.forEach((p) => list.push(makeAtom(p, 'A')))
    edgeCenters.forEach((p) => list.push(makeAtom(p, 'B')))
    list.push(makeAtom(cubeCenter, 'B'))
  } else if (templateKey.value === 'diamond') {
    faceCenters.forEach((p) => list.push(makeAtom(p, 'A')))
    ;[[255, 250], [355, 250], [255, 345], [355, 345]].forEach((p) => list.push(makeAtom(p, 'B')))
  }
  atoms.value = list
}

const clearAtoms = () => {
  atoms.value = []
}

const onAtomClick = (atom) => {
  atom.kind = brush.value
}

const onCanvasClick = (event) => {
  if (!addMode.value) return
  const svg = svgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * W
  const y = ((event.clientY - rect.top) / rect.height) * H
  atoms.value.push(makeAtom([x, y], brush.value))
}

const exportSvg = async () => {
  await nextTick()
  const svg = svgRef.value
  if (!svg) throw new Error('画板未准备好')
  const clone = svg.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('width', String(W))
  clone.setAttribute('height', String(H))
  const xml = new XMLSerializer().serializeToString(clone)
  const svgBlob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = reject
      image.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = W * 2
    canvas.height = H * 2
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    return await new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/png')
    })
  } finally {
    URL.revokeObjectURL(url)
  }
}

const insertToQuestion = async () => {
  if (!visibleAtoms.value.length) {
    ElMessage.warning('先画一个晶胞或添加原子')
    return
  }
  exporting.value = true
  try {
    const blob = await exportSvg()
    if (!blob) throw new Error('导出失败')
    emit('insert', { blob, filename: `crystal-${Date.now()}.png` })
    visible.value = false
  } catch (e) {
    ElMessage.error('晶胞图片生成失败，请重试')
  } finally {
    exporting.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    templateKey.value = 'sc'
    applyTemplate()
  }
})
</script>

<style scoped>
.crystal-wrap { display: flex; flex-direction: column; gap: 12px; }
.crystal-toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding-bottom: 10px; border-bottom: 1px solid var(--border-light);
}
.crystal-toolbar__label { font-size: 13px; color: var(--text-secondary); }
.crystal-main { display: flex; gap: 14px; align-items: stretch; }
.crystal-canvas {
  flex: 1; min-width: 0; border: 1px solid var(--border-color); border-radius: 10px;
  overflow: hidden; background: #fff;
}
.crystal-canvas--add { cursor: crosshair; }
.crystal-canvas svg { display: block; width: 100%; height: auto; max-height: 62vh; }
.crystal-canvas__hint {
  padding: 7px 12px; font-size: 12px; color: var(--text-placeholder);
  background: var(--bg-tertiary); border-top: 1px solid var(--border-light);
}
.crystal-atom { cursor: pointer; }
.crystal-atom:hover circle { stroke: var(--brand-500); stroke-width: 3; }
.crystal-side {
  width: 220px; flex-shrink: 0; border: 1px solid var(--border-color);
  border-radius: 10px; padding: 14px; background: var(--bg-tertiary);
}
.crystal-side__title { font-weight: 600; margin-bottom: 12px; color: var(--text-primary); }
.crystal-stat {
  display: flex; justify-content: space-between; padding: 7px 0;
  border-bottom: 1px dashed var(--border-light); font-size: 13px;
}
.crystal-stat span { color: var(--text-secondary); }
.crystal-stat b { color: var(--brand-600); }
.crystal-legend { display: flex; gap: 16px; margin-top: 12px; font-size: 12px; color: var(--text-secondary); }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 4px; vertical-align: -2px; border: 1px solid #0f172a; }
.dot--a { background: #334155; }
.dot--b { background: #fbbf24; }
.crystal-tip { margin-top: 14px; font-size: 12px; line-height: 1.7; color: var(--text-placeholder); }
.crystal-tip p { margin: 0 0 8px; }
.crystal-footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
@media (max-width: 760px) {
  .crystal-main { flex-direction: column; }
  .crystal-side { width: auto; }
  .crystal-toolbar { gap: 8px; }
}
</style>
