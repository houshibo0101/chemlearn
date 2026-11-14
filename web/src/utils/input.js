/**
 * 向当前获得焦点的输入框插入文本（兼容 Element Plus 的 textarea/input）
 * 通过派发 input 事件让 v-model 同步，光标停在插入内容之后。
 */
export function insertAtActiveInput(text) {
  const el = document.activeElement
  if (!el || (el.tagName !== 'TEXTAREA' && el.tagName !== 'INPUT')) return false
  if (el.disabled || el.readOnly) return false

  const start = typeof el.selectionStart === 'number' ? el.selectionStart : el.value.length
  const end = typeof el.selectionEnd === 'number' ? el.selectionEnd : el.value.length

  if (typeof el.setRangeText === 'function') {
    el.setRangeText(text, start, end, 'end')
  } else {
    el.value = el.value.slice(0, start) + text + el.value.slice(end)
  }
  el.dispatchEvent(new Event('input', { bubbles: true }))
  el.focus()
  return true
}
