/**
 * 题目/选项/解析里的公式渲染
 *
 * 与 markdown.js 的区别：这里不跑 Markdown，只把 LaTeX 片段渲成 KaTeX，
 * 其余文本做 HTML 转义，避免题干里的 "<"、"_" 等被 Markdown 误解析。
 *
 * 支持：
 *   $...$ / \(...\)      行内公式
 *   $$...$$ / \[...\]    块级公式
 *   \ce{...}             化学式（KaTeX mhchem 扩展，可不写 $ 包裹）
 */
import katex from 'katex'
import 'katex/dist/katex.min.css'
import 'katex/contrib/mhchem'

const ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

const escapeHtml = (text) => text.replace(/[&<>"']/g, (ch) => ESCAPE_MAP[ch])

const renderMath = (expr, displayMode) => {
  try {
    return katex.renderToString(expr, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
    })
  } catch {
    return escapeHtml(expr)
  }
}

export function renderFormula(value) {
  if (value === null || value === undefined) return ''
  const source = String(value)
  if (!source) return ''

  const rendered = []
  const stash = (html) => `\u0000${rendered.push(html) - 1}\u0000`

  let text = source
  // 先处理公式，避免公式里的 < > 被后续转义破坏
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_m, f) => stash(renderMath(f.trim(), true)))
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_m, f) => stash(renderMath(f.trim(), true)))
  text = text.replace(/\\\(([^)]+?)\\\)/g, (_m, f) => stash(renderMath(f.trim(), false)))
  text = text.replace(/\$([^\n$]+?)\$/g, (_m, f) => stash(renderMath(f.trim(), false)))
  // 裸 \ce{...}（没写 $）自动按行内公式处理；前面是 $ 的交给上一步
  text = text.replace(/(?<!\$)\\ce\{[^{}]*\}/g, (_m, f) => stash(renderMath(f.trim(), false)))

  text = escapeHtml(text).replace(/\n/g, '<br>')
  // 还原公式片段（占位符里只有数字，不会被转义）
  return text.replace(/\u0000(\d+)\u0000/g, (_m, index) => rendered[Number(index)] || '')
}
