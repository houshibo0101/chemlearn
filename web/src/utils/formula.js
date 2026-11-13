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

// ---------------------------------------------------------------------------
// 纯文本里的化学式自动排版：H2 -> H₂、Ca(OH)2 -> Ca(OH)₂、Fe^3+ -> Fe³⁺
// 只改显示，不改数据库原文，避免影响答案判分。
// ---------------------------------------------------------------------------
const ELEMENTS = new Set((
  'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn '
  + 'Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce '
  + 'Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn '
  + 'Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl '
  + 'Mc Lv Ts Og'
).split(' '))

const SUB_DIGITS = { 0: '₀', 1: '₁', 2: '₂', 3: '₃', 4: '₄', 5: '₅', 6: '₆', 7: '₇', 8: '₈', 9: '₉' }
const SUP_DIGITS = { 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' }

const toSub = (digits) => digits.replace(/\d/g, (d) => SUB_DIGITS[d])
const toSup = (digits) => digits.replace(/\d/g, (d) => SUP_DIGITS[d])

// 连续的“元素/括号/点/电荷”片段；数字只作为元素或括号后的下标
const FORMULA_RE = /(?<![A-Za-z0-9])(?:\d+)?(?:[A-Z][a-z]?\d*|\(\d*|\)\d*|·\d*|•\d*|\^\d*[+-]?|[+-])+/g

function convertFormulaToken(token) {
  const head = token.match(/^(\d*)(.*)$/)
  const coefficient = head[1] || ''
  const body = head[2] || ''
  if (!body) return null

  let out = coefficient
  let index = 0
  let sawElement = false
  let sawScript = false
  let parens = 0

  while (index < body.length) {
    const ch = body[index]

    if (/[A-Z]/.test(ch)) {
      const pair = body.slice(index, index + 2)
      const symbol = /^[A-Z][a-z]$/.test(pair) && ELEMENTS.has(pair) ? pair : ch
      if (!ELEMENTS.has(symbol)) return null
      sawElement = true
      out += symbol
      index += symbol.length

      let end = index
      while (/\d/.test(body[end] || '')) end += 1
      if (end > index) {
        const digits = body.slice(index, end)
        index = end
        // 不带 ^ 的 Fe3+ / O2- 有歧义（电荷还是下标），保守起见不自动处理
        if (body[index] === '+' || body[index] === '-') return null
        out += toSub(digits)
        sawScript = true
      }
      if (body[index] === '+' || body[index] === '-') return null
      continue
    }

    if (ch === '(') {
      parens += 1
      out += ch
      index += 1
      continue
    }

    if (ch === ')') {
      if (parens === 0) return null
      parens -= 1
      out += ch
      index += 1
      let end = index
      while (/\d/.test(body[end] || '')) end += 1
      if (end > index) {
        out += toSub(body.slice(index, end))
        sawScript = true
        index = end
      }
      continue
    }

    if (ch === '·' || ch === '•') {
      out += ch
      index += 1
      // 结晶水系数：CuSO4·5H2O 里的 5 保持正常大小
      let end = index
      while (/\d/.test(body[end] || '')) end += 1
      if (end > index) {
        out += body.slice(index, end)
        index = end
      }
      continue
    }

    if (ch === '^') {
      index += 1
      let end = index
      while (/\d/.test(body[end] || '')) end += 1
      const digits = body.slice(index, end)
      index = end
      const sign = body[index]
      if (sign !== '+' && sign !== '-') return null
      index += 1
      out += toSup(digits) + (sign === '+' ? '⁺' : '⁻')
      sawScript = true
      continue
    }

    return null
  }

  if (parens !== 0 || !sawElement || !sawScript) return null
  return out
}

export function formatChemicalText(text) {
  if (!text) return text
  return String(text).replace(FORMULA_RE, (token) => convertFormulaToken(token) || token)
}

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

  // 普通文本里的化学式自动排版：H2 -> H₂、Ca(OH)2 -> Ca(OH)₂
  text = formatChemicalText(text)

  text = escapeHtml(text).replace(/\n/g, '<br>')
  // 还原公式片段（占位符里只有数字，不会被转义）
  return text.replace(/\u0000(\d+)\u0000/g, (_m, index) => rendered[Number(index)] || '')
}
