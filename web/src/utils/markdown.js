/**
 * Markdown + LaTeX 公式渲染（全站统一入口）
 *
 * 安全：所有输出经过 DOMPurify 消毒后再交给 v-html，
 * 防止 AI 回答 / 题目内容中的恶意 HTML（XSS）。
 * 2026-10-10 新增，AIChat / WrongQuestions / StudentWrong 共用。
 */
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import DOMPurify from 'dompurify'

marked.setOptions({
  breaks: true,
  gfm: true,
})

// 渲染 Markdown + LaTeX 公式，返回已消毒的 HTML
export const renderMarkdown = (content) => {
  if (!content) return ''
  // 先渲染 Markdown
  let html = marked.parse(content)
  // 块级公式 $$...$$
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (m, f) => {
    try { return katex.renderToString(f.trim(), { displayMode: true, throwOnError: false }) } catch { return m }
  })
  // 块级公式 \[...\]
  html = html.replace(/\\\[([\s\S]+?)\\\]/g, (m, f) => {
    try { return katex.renderToString(f.trim(), { displayMode: true, throwOnError: false }) } catch { return m }
  })
  // 行内公式 $...$
  html = html.replace(/\$([^\n$]+?)\$/g, (m, f) => {
    try { return katex.renderToString(f.trim(), { displayMode: false, throwOnError: false }) } catch { return m }
  })
  // 行内公式 \(...\)
  html = html.replace(/\\\(([^)]+?)\\\)/g, (m, f) => {
    try { return katex.renderToString(f.trim(), { displayMode: false, throwOnError: false }) } catch { return m }
  })
  // 兜底：检测 \text{...} 等LaTeX命令（无分隔符的情况）
  html = html.replace(/(\\(?:text|mathrm|mathbf|rightarrow|leftarrow|leftrightarrow|uparrow|downarrow|frac|sqrt|sum|int|lim|Delta|alpha|beta|gamma|theta|lambda|mu|pi|sigma|omega|cdot|times|div|pm|neq|leq|geq|approx|infty)[^\n<]*?)(?=<|$)/g, (m) => {
    if (m.includes('$') || m.includes('\\(') || m.includes('\\[')) return m
    try { return katex.renderToString(m.trim(), { displayMode: false, throwOnError: false }) } catch { return m }
  })
  // 消毒：去除 script/事件属性/javascript: 协议等（保留 KaTeX 的 MathML 输出）
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true, mathMl: true, svg: true } })
}
