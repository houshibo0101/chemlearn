<template>
  <el-dialog v-model="visible" title="元素周期表" width="92%" top="4vh" :close-on-click-modal="true" class="element-picker-dialog">
    <div class="periodic-wrap">
      <div class="periodic-main">
        <div v-for="(row, ri) in TABLE_ROWS" :key="'r' + ri" class="periodic-row">
          <button
            v-for="(symbol, ci) in row"
            :key="'c' + ri + '-' + ci"
            class="element-cell"
            :class="{ 'element-cell--empty': !symbol, 'element-cell--active': symbol === modelValue }"
            :style="symbol ? cellStyle(symbol) : {}"
            :title="symbol ? `${symbol} ${ELEMENT_MAP[symbol]?.name || ''}` : ''"
            :disabled="!symbol"
            @click="pick(symbol)"
          >
            <template v-if="symbol">
              <span class="element-z">{{ ELEMENT_MAP[symbol]?.z }}</span>
              <b class="element-symbol">{{ symbol }}</b>
              <span class="element-name">{{ ELEMENT_MAP[symbol]?.name }}</span>
            </template>
          </button>
        </div>
      </div>

      <div class="periodic-fblock">
        <div class="periodic-fblock__label">镧系</div>
        <div class="periodic-frow">
          <button
            v-for="symbol in F_ROWS[0]"
            :key="'f1-' + symbol"
            class="element-cell element-cell--small"
            :class="{ 'element-cell--active': symbol === modelValue }"
            :style="cellStyle(symbol)"
            :title="`${symbol} ${ELEMENT_MAP[symbol]?.name || ''}`"
            @click="pick(symbol)"
          >
            <span class="element-z">{{ ELEMENT_MAP[symbol]?.z }}</span>
            <b class="element-symbol">{{ symbol }}</b>
            <span class="element-name">{{ ELEMENT_MAP[symbol]?.name }}</span>
          </button>
        </div>
        <div class="periodic-fblock__label">锕系</div>
        <div class="periodic-frow">
          <button
            v-for="symbol in F_ROWS[1]"
            :key="'f2-' + symbol"
            class="element-cell element-cell--small"
            :class="{ 'element-cell--active': symbol === modelValue }"
            :style="cellStyle(symbol)"
            :title="`${symbol} ${ELEMENT_MAP[symbol]?.name || ''}`"
            @click="pick(symbol)"
          >
            <span class="element-z">{{ ELEMENT_MAP[symbol]?.z }}</span>
            <b class="element-symbol">{{ symbol }}</b>
            <span class="element-name">{{ ELEMENT_MAP[symbol]?.name }}</span>
          </button>
        </div>
      </div>

      <div class="periodic-foot">
        <span>点击元素设为当前放置原子</span>
        <span v-if="modelValue" class="periodic-current">
          当前：<i :style="{ background: elementColor(modelValue) }" />
          <b>{{ modelValue }}</b> {{ ELEMENT_MAP[modelValue]?.name }}
        </span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { TABLE_ROWS, F_ROWS, ELEMENT_MAP, elementColor } from '@/utils/periodicTable'

const props = defineProps({
  modelValue: { type: String, default: '' },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'update:open', 'select'])

const visible = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

const cellStyle = (symbol) => {
  const color = elementColor(symbol)
  return {
    background: color,
    borderColor: 'rgba(15,23,42,.25)',
    color: textColor(color),
  }
}

const textColor = (hex) => {
  const value = (hex || '#64748b').replace('#', '')
  const r = parseInt(value.slice(0, 2), 16) / 255
  const g = parseInt(value.slice(2, 4), 16) / 255
  const b = parseInt(value.slice(4, 6), 16) / 255
  return (0.299 * r + 0.587 * g + 0.114 * b) > 0.65 ? '#0f172a' : '#ffffff'
}

const pick = (symbol) => {
  if (!symbol) return
  emit('update:modelValue', symbol)
  emit('select', symbol)
}
</script>

<style scoped>
.periodic-wrap { display: flex; flex-direction: column; gap: 10px; }
.periodic-main { display: flex; flex-direction: column; gap: 3px; min-width: 780px; }
.periodic-row { display: grid; grid-template-columns: repeat(18, 1fr); gap: 3px; }
.element-cell {
  min-height: 44px; border: 1px solid rgba(15,23,42,.25); border-radius: 5px;
  padding: 2px 1px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; cursor: pointer; overflow: hidden; line-height: 1.05;
  transition: transform .12s, box-shadow .12s;
}
.element-cell:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 3px 8px rgba(15,23,42,.18); z-index: 2; }
.element-cell--empty { border-color: transparent; background: transparent !important; cursor: default; }
.element-cell--active { outline: 2px solid #4f46e5; outline-offset: 1px; }
.element-z { font-size: 8px; opacity: .8; }
.element-symbol { font-size: 14px; font-weight: 700; }
.element-name { font-size: 8px; opacity: .9; }
.element-cell--small { min-height: 38px; }
.periodic-fblock { margin-left: 11.1%; width: 88.9%; display: flex; flex-direction: column; gap: 3px; }
.periodic-fblock__label { font-size: 11px; color: #64748b; }
.periodic-frow { display: grid; grid-template-columns: repeat(15, 1fr); gap: 3px; }
.periodic-foot {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; color: #94a3b8; padding-top: 6px; border-top: 1px solid #e2e8f0;
}
.periodic-current { display: flex; align-items: center; gap: 5px; color: #334155; }
.periodic-current i { width: 12px; height: 12px; border-radius: 50%; border: 1px solid #0f172a; }
@media (max-width: 900px) {
  .periodic-main { min-width: 640px; }
  .element-cell { min-height: 34px; }
  .element-name { display: none; }
}
</style>
