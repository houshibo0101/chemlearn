/**
 * 向当前获得焦点的输入框插入文本（兼容 Element Plus 的 textarea/input）
 * 通过派发 input 事件让 v-model 同步，光标停在插入内容之后。
 *
 * @param {string} text 要插入的文字
 * @param {number} [caretOffset] 光标相对插入内容起点的位置（默认停在末尾）
 */
export function insertAtActiveInput(text, caretOffset) {
  const el = getActiveTextInput()
  if (!el) return false
  return insertIntoInput(el, text, caretOffset)
}

let lastTextInput = null

function getLastTextInput() {
  if (lastTextInput && document.contains(lastTextInput) && !lastTextInput.disabled && !lastTextInput.readOnly) {
    return lastTextInput
  }
  return getActiveTextInput()
}

document.addEventListener('focusin', (event) => {
  const el = event.target
  if (!el || (el.tagName !== 'TEXTAREA' && el.tagName !== 'INPUT')) return
  // 自定义条件输入框不算目标题目输入框，避免把条件插到条件框自己里
  if (el.closest && el.closest('.chem-symbol-bar')) return
  if (el.disabled || el.readOnly) return
  lastTextInput = el
}, true)

/** 插入到最后一次编辑的题目输入框：适合先点自定义条件输入框、再插入。 */
export function insertAtLastTextInput(text, caretOffset) {
  const el = getLastTextInput()
  if (!el) return false
  return insertIntoInput(el, text, caretOffset)
}

/**
 * 在等号上方插入条件：
 * - 选中了 "="：直接把这个等号替换成带条件的等号
 * - 光标前紧挨着 "="：替换前面的等号
 * - 否则在光标处插入一个带条件的等号
 */
export function insertConditionAtLastTextInput(condition) {
  const el = getLastTextInput()
  if (!el) return false
  const safe = String(condition || '').trim().replace(/[\\{}[\]]/g, '')
  if (!safe) return false

  const { start, end, value } = selectionOf(el)
  let from = start
  let to = end
  let selected = value.slice(start, end)
  if (!selected.trim()) {
    let i = start - 1
    while (i >= 0 && /\s/.test(value[i])) i -= 1
    if (value[i] === '=') {
      from = i
      to = i + 1
      selected = '='
    }
  } else if (selected.trim() === '=') {
    // 选中等号，保持当前选区替换
  }

  const expr = `$\\overset{${safe}}{=}$`
  replaceSelection(el, expr, from, to)
  setCaret(el, from + expr.length)
  el.focus()
  return true
}

function insertIntoInput(el, text, caretOffset) {
  const { start, end } = selectionOf(el)
  replaceSelection(el, text, start, end)
  setCaret(el, start + (typeof caretOffset === 'number' ? caretOffset : text.length))
  el.focus()
  return true
}

/**
 * 一键插入分数线：生成 $\frac{分子}{分母}$
 * - 选中 "1/2" 这类写法：直接拆成分子分母，光标停在分数后面
 * - 选中其他文字：选中内容做分子，光标停在分母里，接着敲分母
 * - 没有选中：插入空分数，光标停在分子里
 */
export function insertFractionAtActiveInput() {
  const el = getActiveTextInput()
  if (!el) return false

  const { start, end, value } = selectionOf(el)
  const picked = value.slice(start, end).trim()
  const slash = picked.indexOf('/')

  let latex
  let caretOffset
  if (picked && slash > 0 && slash === picked.lastIndexOf('/')) {
    const numerator = picked.slice(0, slash).trim()
    const denominator = picked.slice(slash + 1).trim()
    latex = `$\\frac{${numerator}}{${denominator}}$`
    caretOffset = latex.length
  } else if (picked) {
    latex = `$\\frac{${picked}}{}$`
    caretOffset = latex.length - 2 // 分母的 "}" 之前
  } else {
    latex = '$\\frac{}{}$'
    caretOffset = 7 // "$\frac{" 之后，即分子里
  }

  replaceSelection(el, latex, start, end)
  setCaret(el, start + caretOffset)
  el.focus()
  return true
}

function getActiveTextInput() {
  const el = document.activeElement
  if (!el || (el.tagName !== 'TEXTAREA' && el.tagName !== 'INPUT')) return null
  if (el.disabled || el.readOnly) return null
  return el
}

function selectionOf(el) {
  const value = typeof el.value === 'string' ? el.value : ''
  const start = typeof el.selectionStart === 'number' ? el.selectionStart : value.length
  const end = typeof el.selectionEnd === 'number' ? el.selectionEnd : value.length
  return { start, end, value }
}

function replaceSelection(el, text, start, end) {
  if (typeof el.setRangeText === 'function') {
    el.setRangeText(text, start, end, 'end')
  } else {
    el.value = el.value.slice(0, start) + text + el.value.slice(end)
  }
  el.dispatchEvent(new Event('input', { bubbles: true }))
}

function setCaret(el, at) {
  try {
    const pos = Math.max(0, Math.min(at, el.value.length))
    el.setSelectionRange(pos, pos)
  } catch {
    /* number / email 等输入框不支持选区，忽略 */
  }
}
