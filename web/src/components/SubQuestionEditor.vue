<template>
  <div class="sub-editor">
    <div v-for="(node, i) in modelValue" :key="i" class="sub-row">
      <div class="sub-row__head">
        <span>小问 {{ prefix }}{{ i + 1 }}</span>
        <div>
          <el-button
            v-if="depth < 5"
            link
            type="primary"
            size="small"
            @click="addChild(node)"
          >+ 下级小问</el-button>
          <el-button link type="danger" size="small" @click="removeAt(i)">删除</el-button>
        </div>
      </div>

      <el-input
        v-model="node.content"
        type="textarea"
        :rows="2"
        :placeholder="`小问 ${prefix}${i + 1} 的内容`"
      />

      <div v-if="!hasChildren(node)" class="sub-row__bottom">
        <el-input v-model="node.answer" placeholder="该小问参考答案" />
        <el-input-number v-model="node.score" :min="0" :max="100" size="small" />
      </div>
      <div v-else class="sub-row__sum">下级小计 {{ scoreOf(node) }} 分</div>

      <SubQuestionEditor
        v-if="hasChildren(node)"
        v-model="node.children"
        :prefix="`${prefix}${i + 1}.`"
        :depth="depth + 1"
      />
    </div>

    <el-button v-if="depth < 5" size="small" plain @click="addRoot">+ 添加小问</el-button>
  </div>
</template>

<script setup>
defineOptions({ name: 'SubQuestionEditor' })

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  prefix: { type: String, default: '' },
  depth: { type: Number, default: 0 },
})

const hasChildren = (node) => Array.isArray(node.children) && node.children.length > 0

const scoreOf = (node) => {
  if (hasChildren(node)) {
    return node.children.reduce((sum, child) => sum + scoreOf(child), 0)
  }
  return Number(node.score || 0)
}

const addRoot = () => {
  props.modelValue.push({ content: '', answer: '', score: 1, children: [] })
}

const addChild = (node) => {
  if (!Array.isArray(node.children)) node.children = []
  node.children.push({ content: '', answer: '', score: 1, children: [] })
}

const removeAt = (index) => {
  props.modelValue.splice(index, 1)
}
</script>

<style scoped>
.sub-editor { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.sub-row {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-tertiary);
}
.sub-row__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}
.sub-row__bottom { display: flex; gap: 8px; margin-top: 6px; }
.sub-row__bottom .el-input { flex: 1; }
.sub-row__sum { margin-top: 6px; font-size: 12px; color: var(--text-placeholder); }
</style>
