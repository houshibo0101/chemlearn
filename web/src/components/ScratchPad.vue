<template>
  <div class="scratch-pad" :class="{ 'is-disabled': disabled }">
    <div class="scratch-toolbar">
      <button type="button" class="tool" :class="{ active: tool === 'pen' }" @click="tool = 'pen'">✏️ 笔</button>
      <button type="button" class="tool" :class="{ active: tool === 'eraser' }" @click="tool = 'eraser'">橡皮</button>
      <span class="colors">
        <button
          v-for="c in colors"
          :key="c"
          type="button"
          class="swatch"
          :class="{ active: color === c }"
          :style="{ background: c }"
          :title="'画笔颜色 ' + c"
          @click="color = c; tool = 'pen'"
        />
      </span>
      <button type="button" class="tool" :disabled="!strokes.length" @click="undo">撤销</button>
      <button type="button" class="tool" @click="clear">清空</button>
    </div>
    <div class="canvas-wrap">
      <canvas
        ref="canvasRef"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      />
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const canvasRef = ref(null)
const strokes = ref([])
const tool = ref('pen')
const color = ref('#1f2937')
const colors = ['#1f2937', '#2563eb', '#dc2626']

let ctx = null
let drawing = null
let observer = null
let size = { width: 0, height: 0 }

const PEN_WIDTH = 2
const ERASER_WIDTH = 24

const currentStyle = () => {
  if (tool.value === 'eraser') return { color: '#ffffff', width: ERASER_WIDTH }
  return { color: color.value, width: PEN_WIDTH }
}

const setupCanvas = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  const wrap = canvas.parentElement
  const width = Math.max(1, wrap.clientWidth)
  const height = Math.max(1, wrap.clientHeight)
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.floor(width * dpr)
  canvas.height = Math.floor(height * dpr)
  canvas.style.width = width + 'px'
  canvas.style.height = height + 'px'
  size = { width, height }
  ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  redraw()
}

const redraw = () => {
  if (!ctx) return
  ctx.clearRect(0, 0, size.width, size.height)
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, size.width, size.height)
  for (const stroke of strokes.value) drawStroke(stroke)
  if (drawing) drawStroke(drawing)
}

const drawStroke = (stroke) => {
  const points = stroke.points
  if (!points.length) return
  ctx.strokeStyle = stroke.color
  ctx.lineWidth = stroke.width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  if (points.length === 1) {
    ctx.beginPath()
    ctx.arc(points[0].x, points[0].y, stroke.width / 2, 0, Math.PI * 2)
    ctx.fillStyle = stroke.color
    ctx.fill()
    return
  }
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y)
  ctx.stroke()
}

const pointFromEvent = (event) => {
  const rect = canvasRef.value.getBoundingClientRect()
  return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

const onPointerDown = (event) => {
  if (props.disabled) return
  event.preventDefault()
  canvasRef.value.setPointerCapture?.(event.pointerId)
  const style = currentStyle()
  drawing = { color: style.color, width: style.width, points: [pointFromEvent(event)] }
  redraw()
}

const onPointerMove = (event) => {
  if (!drawing || props.disabled) return
  event.preventDefault()
  const point = pointFromEvent(event)
  const last = drawing.points[drawing.points.length - 1]
  if (last && Math.hypot(point.x - last.x, point.y - last.y) < 0.8) return
  drawing.points.push(point)
  // 只画新增线段，避免整张重绘导致手写延迟
  ctx.strokeStyle = drawing.color
  ctx.lineWidth = drawing.width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  ctx.moveTo(last.x, last.y)
  ctx.lineTo(point.x, point.y)
  ctx.stroke()
}

const onPointerUp = (event) => {
  if (!drawing) return
  canvasRef.value?.releasePointerCapture?.(event.pointerId)
  if (drawing.points.length) strokes.value.push(drawing)
  drawing = null
}

const clear = () => {
  strokes.value = []
  drawing = null
  if (ctx) {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, size.width, size.height)
  }
}

const undo = () => {
  strokes.value.pop()
  redraw()
}

defineExpose({ clear, undo })

onMounted(() => {
  setupCanvas()
  observer = new ResizeObserver(() => setupCanvas())
  if (canvasRef.value?.parentElement) observer.observe(canvasRef.value.parentElement)
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.scratch-pad {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.scratch-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 6px 8px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}
.tool {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  padding: 4px 9px;
  font-size: 12px;
  line-height: 1.4;
  color: #374151;
  cursor: pointer;
  touch-action: manipulation;
}
.tool.active {
  border-color: #4f46e5;
  color: #4f46e5;
  background: #eef2ff;
}
.tool:disabled {
  opacity: 0.45;
  cursor: default;
}
.colors {
  display: flex;
  gap: 4px;
  margin: 0 4px;
}
.swatch {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #cbd5e1;
  cursor: pointer;
  padding: 0;
}
.swatch.active {
  box-shadow: 0 0 0 2px #4f46e5;
}
.canvas-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
  background: #fff;
}
canvas {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
}
.is-disabled canvas {
  cursor: not-allowed;
}
</style>
