<template>
  <span class="math-text" :class="{ 'math-text--inline': inline }" v-html="html"></span>
</template>

<script setup>
import { computed } from 'vue'
import { renderFormula } from '@/utils/formula'

const props = defineProps({
  text: { type: [String, Number], default: '' },
  // 行内场景（选项、表格、卡片）用于收掉块级公式的外边距
  inline: { type: Boolean, default: false },
})

const html = computed(() => renderFormula(props.text))
</script>

<style scoped>
.math-text {
  word-break: break-word;
}
.math-text :deep(.katex) {
  font-size: 1.05em;
}
.math-text :deep(.katex-display) {
  margin: 0.35em 0;
  overflow-x: auto;
  overflow-y: hidden;
}
.math-text--inline {
  display: inline;
}
.math-text--inline :deep(.katex-display) {
  display: inline-block;
  margin: 0;
}
</style>
