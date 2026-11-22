<template>
  <div class="chem-symbol-bar" role="toolbar" aria-label="化学符号与公式快捷输入">
    <button
      v-for="item in items"
      :key="item.label"
      type="button"
      class="chem-symbol-bar__btn"
      :class="{ 'chem-symbol-bar__btn--frac': item.fraction }"
      :title="item.title || item.label"
      @pointerdown.prevent
      @click="pick(item)"
    >
      <span v-if="item.fraction" class="chem-symbol-bar__glyph chem-symbol-bar__glyph--frac">
        <span>a</span>
        <i />
        <span>b</span>
      </span>
      <span v-else-if="item.condition" class="chem-symbol-bar__glyph chem-symbol-bar__glyph--cond">
        <span class="chem-symbol-bar__cond-text">{{ item.display || conditionText(item.condition) }}</span>
        <span class="chem-symbol-bar__cond-arrow">=</span>
      </span>
      <span v-else class="chem-symbol-bar__glyph">{{ item.text }}</span>
      <span class="chem-symbol-bar__label">{{ item.label }}</span>
    </button>
    <span class="chem-symbol-bar__custom">
      <input
        v-model="customCondition"
        class="chem-symbol-bar__custom-input"
        maxlength="24"
        placeholder="自定义条件"
        aria-label="自定义条件"
        @keyup.enter="insertCustom"
      />
      <button
        type="button"
        class="chem-symbol-bar__custom-btn"
        title="把自定义条件写到等号上方"
        @pointerdown.prevent
        @click="insertCustom"
      >插入条件</button>
    </span>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['insert', 'fraction', 'condition'])
const customCondition = ref('')

const insertCustom = () => {
  const condition = String(customCondition.value || '').trim()
  if (!condition) return
  const safe = condition.replace(/[\[\]{}\\]/g, '')
  if (!safe) return
  emit('condition', safe)
  customCondition.value = ''
}

const items = [
  { text: '↑', label: '气体' },
  { text: '↓', label: '沉淀' },
  { text: '→', label: '箭头' },
  { text: '⇌', label: '可逆' },
  { text: 'Δ', label: '加热' },
  { text: '·', label: '结晶水' },
  { text: '⁺', label: '正电荷' },
  { text: '⁻', label: '负电荷' },
  {
    fraction: true,
    label: '分数线',
    title: '插入分数线：先选中 1/2 可直接变上下两行；选中文字则作分子，没选中就插空分数',
  },
  { condition: '点燃', label: '点燃', title: '插入等号上方条件：点燃' },
  { condition: '加热', display: 'Δ', label: '加热条件', title: '插入等号上方条件：加热（Δ）' },
  { condition: '高温', label: '高温', title: '插入等号上方条件：高温' },
  { condition: '催化剂', label: '催化剂', title: '插入等号上方条件：催化剂' },
  { condition: '电解', label: '电解', title: '插入等号上方条件：电解' },
  { condition: '光照', label: '光照', title: '插入等号上方条件：光照' },
]

const conditionText = (condition) => (condition === '\\Delta' ? 'Δ' : condition)

const pick = (item) => {
  if (item.fraction) emit('fraction')
  else if (item.condition) emit('condition', item.condition)
  else emit('insert', item.text)
}
</script>

<style scoped>
.chem-symbol-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.chem-symbol-bar__btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 34px;
  padding: 4px 10px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  touch-action: manipulation;
  line-height: 1;
}
.chem-symbol-bar__btn:hover {
  border-color: var(--brand-500);
  color: var(--brand-600);
  background: var(--bg-hover);
}
.chem-symbol-bar__btn--frac {
  border-style: dashed;
}
.chem-symbol-bar__glyph {
  font-size: 17px;
  font-weight: 600;
}
.chem-symbol-bar__glyph--frac {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.chem-symbol-bar__glyph--frac i {
  display: block;
  width: 13px;
  border-top: 1.4px solid currentColor;
  margin: 1px 0;
}
.chem-symbol-bar__glyph--cond {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  line-height: 1;
}
.chem-symbol-bar__cond-text {
  font-size: 9px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.chem-symbol-bar__cond-arrow {
  font-size: 17px;
  color: var(--text-secondary);
  line-height: 1;
}
.chem-symbol-bar__label {
  font-size: 11px;
  color: var(--text-placeholder);
}
.chem-symbol-bar__custom {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 4px;
  padding-left: 8px;
  border-left: 1px dashed var(--border-strong);
}
.chem-symbol-bar__custom-input {
  width: 110px;
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}
.chem-symbol-bar__custom-input:focus {
  border-color: var(--brand-500);
}
.chem-symbol-bar__custom-btn {
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--brand-500);
  border-radius: 8px;
  background: var(--brand-50, #eef2ff);
  color: var(--brand-600);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
</style>
