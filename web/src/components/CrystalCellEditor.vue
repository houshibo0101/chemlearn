<template>
  <el-dialog
    v-model="visible"
    title="晶胞编辑器 · 3D"
    width="94%"
    top="2vh"
    :close-on-click-modal="false"
  >
    <div class="hou-editor">
      <div class="hou-toolbar">
        <el-input v-model="name" placeholder="晶胞名称" style="width: 180px;" />
        <el-button :icon="Download" @click="downloadHou">保存 .hou</el-button>
        <el-button :icon="Upload" @click="triggerOpen">打开 .hou</el-button>
        <input ref="fileInput" type="file" accept=".hou,application/json" style="display:none" @change="loadHou" />
        <el-checkbox v-model="addMode">点空白添加原子</el-checkbox>
        <span class="hou-toolbar__hint">左键拖动旋转 · 滚轮缩放</span>
        <div class="hou-toolbar__right">
          <el-button @click="resetView">重置视角</el-button>
          <el-button type="primary" :loading="exporting" @click="insertToQuestion">插入到题目</el-button>
        </div>
      </div>

      <div class="hou-main">
        <div class="hou-panel">
          <div class="hou-section">晶胞参数</div>
          <div class="hou-preset">
            <el-select v-model="preset" style="width: 130px;" @change="applyPreset">
              <el-option label="立方晶胞" value="cubic" />
              <el-option label="六方晶胞" value="hex" />
              <el-option label="自定义" value="custom" />
            </el-select>
            <span class="hou-tip">{{ presetText }}</span>
          </div>
          <div class="hou-grid">
            <label>a (Å)<el-input-number v-model="lattice.a" :min="0.1" :max="100" :step="0.1" size="small" /></label>
            <label>b (Å)<el-input-number v-model="lattice.b" :min="0.1" :max="100" :step="0.1" size="small" /></label>
            <label>c (Å)<el-input-number v-model="lattice.c" :min="0.1" :max="100" :step="0.1" size="small" /></label>
            <label>α (°)<el-input-number v-model="lattice.alpha" :min="20" :max="160" :step="1" size="small" /></label>
            <label>β (°)<el-input-number v-model="lattice.beta" :min="20" :max="160" :step="1" size="small" /></label>
            <label>γ (°)<el-input-number v-model="lattice.gamma" :min="20" :max="160" :step="1" size="small" /></label>
          </div>

          <div class="hou-section">原子模板</div>
          <div class="hou-preset">
            <el-select v-model="templateKey" style="width: 130px;">
              <el-option label="不加载" value="none" />
              <el-option label="简单立方" value="sc" />
              <el-option label="体心立方" value="bcc" />
              <el-option label="面心立方" value="fcc" />
              <el-option label="NaCl 型" value="nacl" />
              <el-option label="CsCl 型" value="cscl" />
              <el-option label="金刚石" value="diamond" />
            </el-select>
            <el-button size="small" @click="applyAtomTemplate">应用</el-button>
          </div>

          <div class="hou-section">原子坐标（分数坐标 0–1）</div>
          <div class="hou-add">
            <el-input v-model="newAtom.element" maxlength="3" style="width: 62px;" placeholder="元素" />
            <el-button :icon="Grid" size="small" @click="showPeriodic = true">周期表</el-button>
            <el-input-number v-model="newAtom.x" :min="-1" :max="2" :step="0.125" :precision="3" size="small" controls-position="right" />
            <el-input-number v-model="newAtom.y" :min="-1" :max="2" :step="0.125" :precision="3" size="small" controls-position="right" />
            <el-input-number v-model="newAtom.z" :min="-1" :max="2" :step="0.125" :precision="3" size="small" controls-position="right" />
            <el-button type="primary" size="small" @click="addAtom">添加</el-button>
          </div>
          <div class="hou-atom-list">
            <div v-for="(atom, i) in atoms" :key="atom.id || i" class="hou-atom-row">
              <span class="hou-dot" :style="{ background: elementColor(atom.element) }" />
              <el-input v-model="atom.element" maxlength="3" size="small" style="width: 58px;" />
              <input v-model.number="atom.x" type="number" step="0.125" min="-1" max="2" class="hou-coord-input" />
              <input v-model.number="atom.y" type="number" step="0.125" min="-1" max="2" class="hou-coord-input" />
              <input v-model.number="atom.z" type="number" step="0.125" min="-1" max="2" class="hou-coord-input" />
              <el-button link type="danger" size="small" @click="removeAtom(i)">删除</el-button>
            </div>
            <div v-if="atoms.length === 0" class="hou-empty">还没有原子，可添加或应用模板</div>
          </div>
          <div class="hou-count">共 {{ atoms.length }} 个原子 · 当前元素 {{ newAtom.element }}</div>
        </div>

        <div ref="canvasWrap" class="hou-canvas-wrap">
          <canvas
            ref="canvas"
            class="hou-canvas"
            :class="{ 'hou-canvas--add': addMode }"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointerleave="endDrag"
            @wheel.prevent="onWheel"
          />
          <div class="hou-canvas__hint">
            {{ addMode ? '点击画布放置 ' + (newAtom.element || '原子') + ' · 拖动仍然旋转' : '拖动旋转晶胞 · 滚轮缩放' }}
          </div>
        </div>
      </div>
    </div>
  </el-dialog>

  <ElementPicker
    v-model="newAtom.element"
    v-model:open="showPeriodic"
    @select="chooseElement"
  />
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Upload, Grid } from '@element-plus/icons-vue'
import ElementPicker from '@/components/ElementPicker.vue'
import { elementColor, elementRadius } from '@/utils/periodicTable'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'insert'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const W = 760
const H = 560
const canvas = ref(null)
const canvasWrap = ref(null)
const fileInput = ref(null)
const drawing = ref(false)
const addMode = ref(false)
const exporting = ref(false)
const showPeriodic = ref(false)

const name = ref('晶胞结构')
const preset = ref('cubic')
const templateKey = ref('none')
const lattice = reactive({ a: 4, b: 4, c: 4, alpha: 90, beta: 90, gamma: 90 })
const view = reactive({ rx: 20, ry: -28, zoom: 1 })
const atoms = ref([])
const newAtom = reactive({ element: 'Na', x: 0, y: 0, z: 0 })
let atomSeq = 0
let drag = null
let resizeObserver = null
let lastScene = null

const presetText = computed(() => ({
  cubic: 'a = b = c，α = β = γ = 90°',
  hex: 'a = b，γ = 120°，α = β = 90°',
  custom: '自定义晶胞参数',
}[preset.value] || ''))
const fmt = (v) => Number(v || 0).toFixed(3)

const elementTextColor = (hex) => {
  const value = String(hex || '#64748b').replace('#', '')
  const r = parseInt(value.slice(0, 2), 16) / 255
  const g = parseInt(value.slice(2, 4), 16) / 255
  const b = parseInt(value.slice(4, 6), 16) / 255
  return (0.299 * r + 0.587 * g + 0.114 * b) > 0.62 ? '#0f172a' : '#ffffff'
}

function latticeVectors(l) {
  const rad = Math.PI / 180
  const al = l.alpha * rad, be = l.beta * rad, ga = l.gamma * rad
  const a = [l.a, 0, 0]
  const b = [l.b * Math.cos(ga), l.b * Math.sin(ga), 0]
  const cx = l.c * Math.cos(be)
  const cy = l.c * Math.cos(al) - l.c * Math.cos(be) * Math.cos(ga)
  const cyv = cy / Math.max(Math.sin(ga), 0.0001)
  const cz = Math.sqrt(Math.max(0, l.c * l.c - cx * cx - cyv * cyv))
  return { a, b, c: [cx, cyv, cz] }
}

function cartesian(frac, vecs) {
  const [x, y, z] = frac
  return [
    x * vecs.a[0] + y * vecs.b[0] + z * vecs.c[0],
    x * vecs.a[1] + y * vecs.b[1] + z * vecs.c[1],
    x * vecs.a[2] + y * vecs.b[2] + z * vecs.c[2],
  ]
}

function rotatePoint(p, rx, ry) {
  const [x, y, z] = p
  const sr = Math.sin(ry * Math.PI / 180), cr = Math.cos(ry * Math.PI / 180)
  const x1 = x * cr + z * sr
  const z1 = -x * sr + z * cr
  const sx = Math.sin(rx * Math.PI / 180), cx = Math.cos(rx * Math.PI / 180)
  const y1 = y * cx - z1 * sx
  const z2 = y * sx + z1 * cx
  return [x1, y1, z2]
}

function project(p, scale, cx, cy) {
  const q = rotatePoint(p, view.rx, view.ry)
  return { x: cx + q[0] * scale, y: cy - q[1] * scale, z: q[2] }
}

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
]

function screenToFraction(clientX, clientY) {
  const el = canvas.value
  if (!el || !lastScene) return null
  const rect = el.getBoundingClientRect()
  const sx = clientX - rect.left
  const sy = clientY - rect.top
  const rx = view.rx * Math.PI / 180
  const ry = view.ry * Math.PI / 180
  const x1 = (sx - lastScene.centerX) / lastScene.scale
  const y2 = -(sy - lastScene.centerY) / lastScene.scale
  const z2 = 0
  const y = y2 * Math.cos(rx) + z2 * Math.sin(rx)
  const z1 = -y2 * Math.sin(rx) + z2 * Math.cos(rx)
  const x = x1 * Math.cos(ry) - z1 * Math.sin(ry)
  const z = x1 * Math.sin(ry) + z1 * Math.cos(ry)
  const world = [x + lastScene.center[0], y + lastScene.center[1], z + lastScene.center[2]]
  const { a, b, c } = lastScene.vecs
  const det = dot(a, cross(b, c))
  if (Math.abs(det) < 1e-8) return null
  const round = (v) => Math.round(v * 8) / 8
  return [
    round(dot(world, cross(b, c)) / det),
    round(dot(world, cross(c, a)) / det),
    round(dot(world, cross(a, b)) / det),
  ]
}

function placeAtomAtPointer(event) {
  if (!addMode.value) return
  const frac = screenToFraction(event.clientX, event.clientY)
  if (!frac) return
  const element = String(newAtom.element || '').trim() || 'C'
  atoms.value.push(makeAtom(element, frac[0], frac[1], frac[2]))
  newAtom.x = frac[0]
  newAtom.y = frac[1]
  newAtom.z = frac[2]
  render()
  ElMessage.success(`已放置 ${element} 到 (${frac.map((v) => v.toFixed(3)).join(', ')})`)
}

function computeScene() {
  const vecs = latticeVectors(lattice)
  const corners = []
  for (const x of [0, 1]) for (const y of [0, 1]) for (const z of [0, 1]) corners.push([x, y, z])
  const cornerCart = corners.map((f) => cartesian(f, vecs))
  const center = [0, 1, 2].map((i) => cornerCart.reduce((s, p) => s + p[i], 0) / 8)
  const shifted = cornerCart.map((p) => [p[0] - center[0], p[1] - center[1], p[2] - center[2]])
  const radius = Math.max(1, ...shifted.map((p) => Math.hypot(...p)))
  const scale = Math.min(W, H) * 0.36 / radius * view.zoom
  const atomPoints = atoms.value.map((atom) => {
    const p = cartesian([Number(atom.x) || 0, Number(atom.y) || 0, Number(atom.z) || 0], vecs)
    const rel = [p[0] - center[0], p[1] - center[1], p[2] - center[2]]
    return { atom, point: project(rel, scale, W / 2, H / 2) }
  })
  return { corners: shifted.map((p) => project(p, scale, W / 2, H / 2)), atomPoints, scale }
}

const edges = [
  [0, 1], [1, 3], [3, 2], [2, 0],
  [4, 5], [5, 7], [7, 6], [6, 4],
  [0, 4], [1, 5], [2, 6], [3, 7],
]

function resizeCanvas() {
  const el = canvas.value
  const wrap = canvasWrap.value
  if (!el || !wrap) return
  const rect = wrap.getBoundingClientRect()
  const w = Math.max(320, Math.floor(rect.width))
  const h = Math.max(360, Math.floor(rect.height))
  const dpr = window.devicePixelRatio || 1
  el.width = w * dpr
  el.height = h * dpr
  el.style.width = `${w}px`
  el.style.height = `${h}px`
  const ctx = el.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  render(w, h)
}

function render(w = W, h = H) {
  const el = canvas.value
  if (!el) return
  const ctx = el.getContext('2d')
  const cw = w || el.clientWidth || W
  const ch = h || el.clientHeight || H
  ctx.clearRect(0, 0, cw, ch)
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, cw, ch)

  // 用实际 canvas 尺寸重算投影，保证宽屏/窄屏居中
  const vecs = latticeVectors(lattice)
  const cornerCart = []
  for (const x of [0, 1]) for (const y of [0, 1]) for (const z of [0, 1]) {
    cornerCart.push(cartesian([x, y, z], vecs))
  }
  const center = [0, 1, 2].map((i) => cornerCart.reduce((s, p) => s + p[i], 0) / 8)
  const shifted = cornerCart.map((p) => [p[0] - center[0], p[1] - center[1], p[2] - center[2]])
  const radius = Math.max(1, ...shifted.map((p) => Math.hypot(...p)))
  const scale = Math.min(cw, ch) * 0.38 / radius * view.zoom
  const centerX = cw / 2, centerY = ch / 2
  lastScene = { scale, centerX, centerY, center, vecs }
  const corners = shifted.map((p) => project(p, scale, centerX, centerY))

  ctx.strokeStyle = '#94a3b8'
  ctx.lineWidth = 1.6
  for (const [i, j] of edges) {
    ctx.beginPath()
    ctx.moveTo(corners[i].x, corners[i].y)
    ctx.lineTo(corners[j].x, corners[j].y)
    ctx.stroke()
  }

  // 晶胞轴 a/b/c
  const origin = project([-center[0], -center[1], -center[2]], scale, centerX, centerY)
  const axes = [
    { v: cartesian([1, 0, 0], vecs), label: 'a', color: '#6366f1' },
    { v: cartesian([0, 1, 0], vecs), label: 'b', color: '#10b981' },
    { v: cartesian([0, 0, 1], vecs), label: 'c', color: '#f59e0b' },
  ]
  for (const axis of axes) {
    const p = project([axis.v[0] - center[0], axis.v[1] - center[1], axis.v[2] - center[2]], scale, centerX, centerY)
    ctx.strokeStyle = axis.color
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(origin.x, origin.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()
    ctx.fillStyle = axis.color
    ctx.font = 'bold 11px Microsoft YaHei, Arial'
    ctx.fillText(axis.label, p.x + 4, p.y - 4)
  }

  const points = atoms.value.map((atom) => {
    const p = cartesian([Number(atom.x) || 0, Number(atom.y) || 0, Number(atom.z) || 0], vecs)
    return {
      atom,
      p: project([p[0] - center[0], p[1] - center[1], p[2] - center[2]], scale, centerX, centerY),
    }
  }).sort((a, b) => a.p.z - b.p.z)

  for (const item of points) {
    const r = Math.max(4, Math.min(17, elementRadius(item.atom.element) * scale * 1.15))
    ctx.beginPath()
    ctx.arc(item.p.x, item.p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = elementColor(item.atom.element)
    ctx.fill()
    ctx.strokeStyle = '#0f172a'
    ctx.lineWidth = 1.2
    ctx.stroke()
    const label = String(item.atom.element || '').trim()
    if (label && r >= 6) {
      ctx.fillStyle = elementTextColor(elementColor(item.atom.element))
      ctx.font = `${Math.max(8, Math.min(12, r))}px Microsoft YaHei, Arial`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, item.p.x, item.p.y + 0.5)
      ctx.textAlign = 'start'
      ctx.textBaseline = 'alphabetic'
    }
  }
  ctx.fillStyle = '#94a3b8'
  ctx.font = '11px Microsoft YaHei, Arial'
  ctx.fillText('拖动旋转 · 滚轮缩放', 14, ch - 14)
}

function onPointerDown(e) {
  drag = { x: e.clientX, y: e.clientY, rx: view.rx, ry: view.ry, moved: false }
  canvas.value.setPointerCapture?.(e.pointerId)
  drawing.value = true
}
function onPointerMove(e) {
  if (!drag) return
  if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 4) drag.moved = true
  view.ry = drag.ry + (e.clientX - drag.x) * 0.55
  view.rx = drag.rx - (e.clientY - drag.y) * 0.55
  view.rx = Math.max(-89, Math.min(89, view.rx))
  render()
}
function onPointerUp(e) {
  const wasClick = drag && !drag.moved
  endDrag()
  if (wasClick && addMode.value) placeAtomAtPointer(e)
}
function endDrag() { drag = null; drawing.value = false }
function onWheel(e) {
  view.zoom = Math.max(0.35, Math.min(3, view.zoom * (e.deltaY > 0 ? 0.92 : 1.08)))
  render()
}
function resetView() {
  view.rx = 20; view.ry = -28; view.zoom = 1
  render()
}

function applyPreset() {
  if (preset.value === 'cubic') {
    lattice.alpha = 90; lattice.beta = 90; lattice.gamma = 90
    if (lattice.a === lattice.b && lattice.b === lattice.c) { /* keep */ }
  } else if (preset.value === 'hex') {
    lattice.b = lattice.a
    lattice.alpha = 90; lattice.beta = 90; lattice.gamma = 120
    lattice.c = Math.max(lattice.c, 1)
  }
  render()
}

function makeAtom(element, x, y, z) {
  return { id: ++atomSeq, element, x, y, z }
}

const CELL_CORNERS = [
  [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
  [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
]
const FACE_CENTERS = [
  [0.5, 0.5, 0], [0.5, 0.5, 1], [0.5, 0, 0.5],
  [0.5, 1, 0.5], [0, 0.5, 0.5], [1, 0.5, 0.5],
]
const EDGE_CENTERS = [
  [0.5, 0, 0], [0.5, 1, 0], [0.5, 0, 1], [0.5, 1, 1],
  [0, 0.5, 0], [1, 0.5, 0], [0, 0.5, 1], [1, 0.5, 1],
  [0, 0, 0.5], [1, 0, 0.5], [0, 1, 0.5], [1, 1, 0.5],
]
const DIAMOND_INNER = [
  [0.25, 0.25, 0.25], [0.75, 0.75, 0.25],
  [0.75, 0.25, 0.75], [0.25, 0.75, 0.75],
]

const atomsOf = (coords, element) => coords.map(([x, y, z]) => makeAtom(element, x, y, z))

const templates = {
  sc: () => atomsOf(CELL_CORNERS, 'C'),
  bcc: () => [...atomsOf(CELL_CORNERS, 'C'), makeAtom('C', 0.5, 0.5, 0.5)],
  fcc: () => [...atomsOf(CELL_CORNERS, 'C'), ...atomsOf(FACE_CENTERS, 'C')],
  nacl: () => [
    ...atomsOf(CELL_CORNERS, 'Cl'),
    ...atomsOf(FACE_CENTERS, 'Cl'),
    ...atomsOf(EDGE_CENTERS, 'Na'),
    makeAtom('Na', 0.5, 0.5, 0.5),
  ],
  cscl: () => [...atomsOf(CELL_CORNERS, 'Cl'), makeAtom('Cs', 0.5, 0.5, 0.5)],
  diamond: () => [
    ...atomsOf(CELL_CORNERS, 'C'),
    ...atomsOf(FACE_CENTERS, 'C'),
    ...atomsOf(DIAMOND_INNER, 'C'),
  ],
}

function applyAtomTemplate() {
  if (templateKey.value === 'none') return
  const fn = templates[templateKey.value]
  if (fn) {
    atoms.value = fn()
    if (preset.value === 'hex') preset.value = 'cubic'
    if (['sc', 'bcc', 'fcc', 'nacl', 'cscl', 'diamond'].includes(templateKey.value)) {
      if (lattice.a === lattice.b && lattice.b === lattice.c && lattice.gamma === 90) {
        // keep cubic parameters
      }
    }
    render()
  }
}

const addAtom = () => {
  const element = String(newAtom.element || '').trim()
  if (!element) { ElMessage.warning('请输入元素符号'); return }
  atoms.value.push(makeAtom(element, Number(newAtom.x) || 0, Number(newAtom.y) || 0, Number(newAtom.z) || 0))
  render()
}

const chooseElement = (symbol) => {
  newAtom.element = symbol
  addMode.value = true
  showPeriodic.value = false
  ElMessage.success(`已选择 ${symbol}，点击画布放置原子`)
}
const removeAtom = (i) => { atoms.value.splice(i, 1); render() }

function downloadHou() {
  const data = {
    format: 'hou-crystal',
    version: 1,
    name: name.value || '晶胞结构',
    lattice: { ...lattice },
    atoms: atoms.value.map(({ element, x, y, z }) => ({
      element: String(element || '').trim() || 'C',
      x: Number(x) || 0, y: Number(y) || 0, z: Number(z) || 0,
    })),
    view: { rx: view.rx, ry: view.ry, zoom: view.zoom },
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(name.value || 'crystal').replace(/[\\/:*?"<>|]/g, '_')}.hou`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('.hou 文件已保存')
}

const triggerOpen = () => fileInput.value?.click()
const loadHou = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    if (data.format !== 'hou-crystal') throw new Error('不是 .hou 晶胞文件')
    if (data.name) name.value = data.name
    if (data.lattice) Object.assign(lattice, data.lattice)
    if (data.view) Object.assign(view, data.view)
    atoms.value = (data.atoms || []).map((a) => makeAtom(
      a.element || 'C', Number(a.x) || 0, Number(a.y) || 0, Number(a.z) || 0,
    ))
    templateKey.value = 'none'
    await nextTick()
    render()
    ElMessage.success('已载入 .hou 晶胞')
  } catch (e) {
    ElMessage.error('无法读取 .hou 文件：' + (e.message || e))
  }
}

const insertToQuestion = async () => {
  if (!atoms.value.length) {
    ElMessage.warning('至少添加一个原子')
    return
  }
  exporting.value = true
  try {
    const el = canvas.value
    if (!el) throw new Error('画布未准备好')
    const blob = await new Promise((resolve) => el.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('导出失败')
    emit('insert', { blob, filename: `crystal-${Date.now()}.png` })
    visible.value = false
  } catch (e) {
    ElMessage.error('晶胞图片生成失败，请重试')
  } finally {
    exporting.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (!open) return
  if (!atoms.value.length) {
    templateKey.value = 'sc'
    atoms.value = templates.sc()
  }
  await nextTick()
  setTimeout(() => {
    resizeObserver?.disconnect()
    resizeObserver = new ResizeObserver(() => resizeCanvas())
    if (canvasWrap.value) resizeObserver.observe(canvasWrap.value)
    resizeCanvas()
  }, 60)
})

watch([lattice, view], () => render(), { deep: true })
watch(atoms, () => render(), { deep: true })
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<style scoped>
.hou-editor { display: flex; flex-direction: column; gap: 12px; }
.hou-toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding-bottom: 10px; border-bottom: 1px solid var(--border-light);
}
.hou-toolbar__hint { color: var(--text-placeholder); font-size: 12px; }
.hou-toolbar__right { margin-left: auto; display: flex; gap: 8px; }
.hou-main { display: flex; gap: 14px; align-items: stretch; }
.hou-panel {
  width: 390px; flex-shrink: 0; border: 1px solid var(--border-color);
  border-radius: 10px; background: var(--bg-tertiary); padding: 12px;
  max-height: 70vh; overflow: auto;
}
.hou-section {
  font-size: 12px; font-weight: 600; color: var(--text-secondary);
  margin: 12px 0 8px; padding-left: 7px; border-left: 3px solid var(--brand-500);
}
.hou-section:first-child { margin-top: 0; }
.hou-preset { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.hou-tip { font-size: 11px; color: var(--text-placeholder); }
.hou-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px 10px; }
.hou-grid label { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-secondary); }
.hou-grid .el-input-number { width: 86px; }
.hou-add { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.hou-add .el-input-number { width: 62px; }
.hou-atom-list { max-height: 250px; overflow: auto; border-top: 1px solid var(--border-light); }
.hou-atom-row {
  display: flex; align-items: center; gap: 5px; padding: 5px 2px;
  border-bottom: 1px solid var(--border-light); font-size: 11px;
}
.hou-dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid #0f172a; flex-shrink: 0; }
.hou-coord { width: 45px; text-align: right; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.hou-coord-input {
  width: 46px; padding: 4px 3px; border: 1px solid var(--border-color);
  border-radius: 4px; font-size: 11px; text-align: right; background: #fff;
  color: var(--text-primary); font-variant-numeric: tabular-nums;
}
.hou-coord-input:focus { outline: none; border-color: var(--brand-500); }
.hou-empty { padding: 14px 4px; color: var(--text-placeholder); font-size: 12px; }
.hou-count { margin-top: 8px; font-size: 11px; color: var(--text-placeholder); }
.hou-canvas-wrap {
  flex: 1; min-width: 0; height: min(62vh, 620px); max-height: 62vh;
  border: 1px solid var(--border-color); border-radius: 10px;
  overflow: hidden; background: #fff; position: relative;
}
.hou-canvas {
  position: absolute; inset: 0; display: block; width: 100%; height: 100%;
  touch-action: none; cursor: grab;
}
.hou-canvas:active { cursor: grabbing; }
.hou-canvas--add { cursor: crosshair; }
.hou-canvas--add:active { cursor: crosshair; }
.hou-canvas__hint {
  position: absolute; right: 12px; bottom: 10px; font-size: 11px;
  color: var(--text-placeholder); background: rgba(255,255,255,.8);
  padding: 3px 7px; border-radius: 4px; pointer-events: none;
}
@media (max-width: 900px) {
  .hou-main { flex-direction: column; }
  .hou-panel { width: auto; max-height: 36vh; }
  .hou-canvas-wrap { height: 44vh; max-height: 44vh; min-height: 300px; }
}
</style>
