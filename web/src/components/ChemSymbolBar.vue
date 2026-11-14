<template>
  <div class="chem-symbol-bar" role="toolbar" aria-label="化学符号快捷输入">
    <button
      v-for="item in items"
      :key="item.text"
      type="button"
      class="chem-symbol-bar__btn"
      :title="item.label"
      @pointerdown.prevent
      @click="$emit('insert', item.text)"
    >
      <span class="chem-symbol-bar__glyph">{{ item.text }}</span>
      <span class="chem-symbol-bar__label">{{ item.label }}</span>
    </button>
  </div>
</template>

<script setup>
defineEmits(['insert'])

const items = [
  { text: '↑', label: '气体' },
  { text: '↓', label: '沉淀' },
  { text: '→', label: '箭头' },
  { text: '⇌', label: '可逆' },
  { text: 'Δ', label: '加热' },
  { text: '·', label: '结晶水' },
  { text: '⁺', label: '正电荷' },
  { text: '⁻', label: '负电荷' },
]
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
.chem-symbol-bar__glyph {
  font-size: 17px;
  font-weight: 600;
}
.chem-symbol-bar__label {
  font-size: 11px;
  color: var(--text-placeholder);
}
</style>
