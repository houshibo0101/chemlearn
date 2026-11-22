"""
套卷做题页 HTML 模板

设计原则：
  · 单文件、零外部依赖（离线双击也能做题，只是提交不了成绩）
  · 样式与系统一致（靛蓝品牌色），打印友好
  · 数据用 __PAPER_DATA__ 占位符注入，避免与 JS 的花括号冲突

提交接口用相对路径 'submit'：
  页面地址 /api/v1/papers/12/page  →  POST /api/v1/papers/12/submit
  这样无论部署在 /chem 还是根路径，都不需要额外配置。
"""

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>__PAPER_TITLE__</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  :root {
    --brand: #4F46E5;
    --brand-light: #EEF2FF;
    --brand-dark: #4338CA;
    --ok: #10B981;
    --ok-light: #ECFDF5;
    --bad: #EF4444;
    --bad-light: #FEF2F2;
    --text: #0F172A;
    --text-2: #475569;
    --text-3: #94A3B8;
    --line: #E2E8F0;
    --bg: #F4F6FB;
    --card: #FFFFFF;
  }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    font-size: 15px; line-height: 1.7;
  }
  .wrap { max-width: 860px; margin: 0 auto; padding: 0 16px 90px; }

  /* ---------- 顶部固定栏 ---------- */
  .bar {
    position: sticky; top: 0; z-index: 20;
    background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--line);
  }
  .bar__in {
    max-width: 860px; margin: 0 auto; padding: 10px 16px;
    display: flex; align-items: center; gap: 12px;
  }
  .bar__title { font-size: 14.5px; font-weight: 700; flex: 1; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar__back {
    width: 30px; height: 30px; flex-shrink: 0; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-2); background: #F1F5F9; text-decoration: none;
    font-size: 15px; transition: .15s;
  }
  .bar__back:hover { background: #E2E8F0; color: var(--text); }
  .cheat-chip {
    font-size: 11.5px; color: #B45309; background: #FFFBEB;
    border: 1px solid #FDE68A; padding: 2px 8px; border-radius: 99px;
    white-space: nowrap;
  }
  .timer {
    font-variant-numeric: tabular-nums; font-weight: 700; font-size: 15px;
    color: var(--brand); background: var(--brand-light);
    padding: 4px 10px; border-radius: 8px; letter-spacing: .02em;
  }
  .timer.warn { color: #B45309; background: #FFFBEB; }
  .timer.danger { color: #B91C1C; background: var(--bad-light); animation: pulse 1s infinite; }
  @keyframes pulse { 50% { opacity: .55; } }

  /* ---------- 卷头 ---------- */
  .head { padding: 22px 0 14px; }
  .head h1 { font-size: 20px; margin: 0 0 8px; line-height: 1.4; letter-spacing: -.01em; }
  .head .meta { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12.5px; color: var(--text-3); }
  .head .meta span { background: #fff; border: 1px solid var(--line); padding: 2px 9px; border-radius: 99px; }

  /* ---------- 题号导航 ---------- */
  .nav {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 10px 12px; margin-bottom: 16px;
    display: flex; flex-wrap: wrap; gap: 6px;
  }
  .nav b { font-weight: 500; font-size: 12.5px; color: var(--text-3); margin-right: 6px; align-self: center; }
  .nav a {
    width: 30px; height: 30px; border-radius: 8px; display: flex;
    align-items: center; justify-content: center; font-size: 12.5px;
    color: var(--text-2); background: #F8FAFC; border: 1px solid var(--line);
    text-decoration: none; font-variant-numeric: tabular-nums; transition: .15s;
  }
  .nav a.done { background: var(--brand-light); border-color: #C7D2FE; color: var(--brand-dark); font-weight: 600; }
  .nav a.cur { outline: 2px solid var(--brand); outline-offset: 1px; }

  /* ---------- 题目卡片 ---------- */
  .q {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 18px 20px; margin-bottom: 14px; scroll-margin-top: 64px;
  }
  #resultBox { scroll-margin-top: 60px; }
  .q__head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
  .q__no {
    width: 24px; height: 24px; border-radius: 7px; background: var(--brand);
    color: #fff; font-size: 12.5px; font-weight: 700; display: flex;
    align-items: center; justify-content: center; flex-shrink: 0;
  }
  .q__type { font-size: 11.5px; color: var(--text-3); background: #F1F5F9; padding: 1px 8px; border-radius: 99px; }
  .q__score { margin-left: auto; font-size: 12px; color: var(--text-3); }
  .q__title { font-size: 15px; margin-bottom: 8px; white-space: pre-wrap; }
  .q__content { font-size: 14px; color: var(--text-2); white-space: pre-wrap; margin-bottom: 10px; }

  .opts { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
  .opt {
    display: flex; gap: 10px; align-items: flex-start;
    border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px;
    cursor: pointer; transition: .15s; background: #fff; white-space: pre-wrap;
  }
  .opt:hover { border-color: #C7D2FE; background: #FAFAFF; }
  .opt__key {
    width: 22px; height: 22px; border-radius: 6px; background: #F1F5F9;
    display: flex; align-items: center; justify-content: center;
    font-size: 12.5px; font-weight: 700; color: var(--text-2); flex-shrink: 0;
  }
  .opt.on { border-color: var(--brand); background: var(--brand-light); }
  .opt.on .opt__key { background: var(--brand); color: #fff; }

  .blank {
    width: 100%; margin-top: 10px; padding: 10px 12px; font-size: 14px;
    border: 1px solid var(--line); border-radius: 10px; font-family: inherit;
    resize: vertical; min-height: 44px; outline: none;
  }
  .blank:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(79,70,229,.12); }

  /* 填空题的多个小问 */
  .sub-list { margin-top: 10px; display: flex; flex-direction: column; gap: 10px; }
  .sub-q {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 10px 12px;
    background: #fafbff;
  }
  .sub-q__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }
  .sub-q__no { color: var(--brand); font-weight: 600; font-size: 13px; }
  .sub-q__score { color: var(--text-3); font-size: 12px; }
  .sub-q__content { color: var(--text-1); font-size: 14px; line-height: 1.7; margin-bottom: 6px; white-space: pre-wrap; }
  .sub-q .blank { margin-top: 4px; }

  /* 原卷配图 */
  .fig { margin-top: 12px; }
  .fig img {
    max-width: 100%; max-height: 560px; object-fit: contain; display: block;
    border: 1px solid var(--line); border-radius: 10px; background: #fff;
  }
  .fig__tip { font-size: 11.5px; color: var(--text-3); margin-top: 6px; }
  .fig img.zoomable { cursor: zoom-in; }

  /* ---------- 图片预览（不出页面，避免触发切屏检测） ---------- */
  .img-viewer {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(15, 23, 42, .88);
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .img-viewer.open { display: flex; }
  .img-viewer img {
    max-width: 95vw;
    max-height: 90vh;
    object-fit: contain;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, .35);
  }
  .img-viewer__close {
    position: absolute;
    top: 14px;
    right: 18px;
    width: 40px;
    height: 40px;
    border: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, .18);
    color: #fff;
    font-size: 28px;
    line-height: 1;
    cursor: pointer;
  }
  .img-viewer__close:hover { background: rgba(255, 255, 255, .3); }
  .img-viewer__hint {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 14px;
    text-align: center;
    color: rgba(255, 255, 255, .75);
    font-size: 12px;
    pointer-events: none;
  }

  /* ---------- 判分后状态 ---------- */
  .q.right { border-color: #A7F3D0; }
  .q.wrong { border-color: #FECACA; }
  .tag { font-size: 11.5px; padding: 1px 8px; border-radius: 99px; font-weight: 600; }
  .tag.right { background: var(--ok-light); color: #047857; }
  .tag.wrong { background: var(--bad-light); color: #B91C1C; }
  .opt.correct { border-color: var(--ok); background: var(--ok-light); }
  .opt.mistake { border-color: var(--bad); background: var(--bad-light); }
  .ans { margin-top: 12px; padding: 12px 14px; background: #F8FAFC; border-radius: 10px; font-size: 13.5px; }
  .ans__row { margin-bottom: 4px; }
  .ans__row:last-child { margin-bottom: 0; }
  .ans b { color: var(--text); }
  .ans .ok { color: #047857; font-weight: 700; }
  .ans .no { color: #B91C1C; font-weight: 700; }
  .ans__reason { color: var(--text-3); font-size: 12.5px; }

  .selfjudge { margin-top: 10px; display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--text-2); }

  /* ---------- 底部操作 ---------- */
  .submit-bar {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;
    background: rgba(255,255,255,.95); backdrop-filter: blur(10px);
    border-top: 1px solid var(--line); padding: 10px 16px;
  }
  .submit-bar__in { max-width: 860px; margin: 0 auto; display: flex; align-items: center; gap: 12px; }
  .submit-bar__stat { font-size: 13px; color: var(--text-2); flex: 1; }
  .submit-bar__stat b { color: var(--brand); font-size: 15px; }
  button { font-family: inherit; cursor: pointer; border: none; }
  .btn {
    background: var(--brand); color: #fff; font-size: 14.5px; font-weight: 600;
    padding: 10px 22px; border-radius: 10px; transition: .15s;
  }
  .btn:hover { background: var(--brand-dark); }
  .btn:disabled { opacity: .5; cursor: not-allowed; }
  .btn--ghost { background: #fff; color: var(--text-2); border: 1px solid var(--line); font-weight: 500; }
  .btn--sm { padding: 6px 12px; font-size: 13px; border-radius: 8px; }

  /* ---------- 分数渲染（离线可用，不引 KaTeX） ---------- */
  .mfrac {
    display: inline-flex; flex-direction: column; align-items: center;
    vertical-align: middle; margin: 0 2px; font-size: .95em; line-height: 1.15;
  }
  .mfrac__n { padding: 0 .3em .05em; border-bottom: 1px solid currentColor; }
  .mfrac__d { padding: .05em .3em 0; }
  .mcond {
    display: inline-flex; flex-direction: column; align-items: center;
    vertical-align: middle; margin: 0 2px; line-height: 1.05;
  }
  .mcond__txt { font-size: .68em; color: var(--text-2); white-space: nowrap; }
  .mcond__arrow { font-size: 1.05em; }

  /* ---------- 符号 / 分数线 插入 ---------- */
  .blank-prev {
    display: none; margin-top: 6px; padding: 6px 10px;
    background: #F8FAFC; border: 1px dashed var(--line); border-radius: 8px;
    font-size: 13px; color: var(--text-2);
  }
  .blank-prev.show { display: block; }
  .sym-panel {
    position: absolute; left: 0; right: 0; bottom: 100%;
    background: rgba(255,255,255,.98); border-top: 1px solid var(--line);
    padding: 8px 16px; display: none;
  }
  .sym-panel.open { display: block; }
  .sym-panel__in {
    max-width: 860px; margin: 0 auto; display: flex; flex-wrap: wrap;
    gap: 6px; align-items: center;
  }
  .sym-panel__hint { font-size: 12px; color: var(--text-3); margin-right: 2px; }
  .sym-btn {
    min-height: 32px; padding: 2px 10px; border-radius: 8px;
    background: #fff; border: 1px solid var(--line); color: var(--text);
    font-size: 15px; line-height: 1.2;
  }
  .sym-btn:hover { border-color: var(--brand); color: var(--brand-dark); }
  .sym-input {
    height: 30px; width: 120px; padding: 0 8px;
    border: 1px solid var(--line); border-radius: 8px;
    background: #fff; color: var(--text); font-size: 12px; outline: none;
  }
  .sym-input:focus { border-color: var(--brand); }
  .sym-btn--frac {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 12px; border-style: dashed;
  }
  .frac-ico {
    display: inline-flex; flex-direction: column; align-items: center;
    font-size: 9px; line-height: 1.05; font-weight: 700;
  }
  .frac-ico i { display: block; width: 12px; border-top: 1.4px solid currentColor; margin: 1px 0; }

  /* ---------- 成绩卡 ---------- */
  .result {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 22px; margin: 16px 0; text-align: center;
  }
  .result__score { font-size: 42px; font-weight: 800; color: var(--brand); line-height: 1.1; letter-spacing: -.02em; }
  .result__score small { font-size: 15px; font-weight: 500; color: var(--text-3); }
  .result__row { display: flex; justify-content: center; gap: 26px; margin-top: 14px; font-size: 13px; color: var(--text-2); }
  .result__row b { display: block; font-size: 17px; color: var(--text); font-variant-numeric: tabular-nums; }
  .result__tip { margin-top: 14px; font-size: 12.5px; color: var(--text-3); }

  .toast {
    position: fixed; left: 50%; top: 64px; transform: translateX(-50%) translateY(-12px);
    background: #0F172A; color: #fff; font-size: 13px; padding: 9px 16px;
    border-radius: 10px; opacity: 0; transition: .25s; pointer-events: none; z-index: 50;
  }
  .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

  @media (max-width: 560px) {
    body { font-size: 14.5px; }
    .wrap { padding: 0 12px 84px; }
    .q { padding: 14px 14px; }
    .result__score { font-size: 36px; }
  }
  @media print {
    .bar, .submit-bar, .nav, .toast { display: none !important; }
    body { background: #fff; }
    .q { break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="bar">
  <div class="bar__in">
    <a class="bar__back" href="../../../../app/papers" title="返回套卷列表">←</a>
    <div class="bar__title">__PAPER_TITLE__</div>
    <span class="cheat-chip" id="cheatChip" style="display:none;"></span>
    <div class="timer" id="timer">--:--</div>
    <button class="btn btn--sm" id="btnTop">交卷</button>
  </div>
</div>

<div class="wrap">
  <div class="head">
    <h1>__PAPER_TITLE__</h1>
    <div class="meta" id="meta"></div>
  </div>
  <div id="resultBox"></div>
  <div class="nav" id="nav"><b>题号</b></div>
  <div id="list"></div>
</div>

<div class="submit-bar" id="submitBar">
  <div class="sym-panel" id="symPanel">
    <div class="sym-panel__in">
      <span class="sym-panel__hint">先点一下答案框，再点下面：</span>
      <button class="sym-btn" type="button" data-sym="↑" title="气体">↑</button>
      <button class="sym-btn" type="button" data-sym="↓" title="沉淀">↓</button>
      <button class="sym-btn" type="button" data-sym="→" title="箭头">→</button>
      <button class="sym-btn" type="button" data-sym="⇌" title="可逆">⇌</button>
      <button class="sym-btn" type="button" data-sym="Δ" title="加热">Δ</button>
      <button class="sym-btn" type="button" data-sym="·" title="结晶水">·</button>
      <button class="sym-btn" type="button" data-sym="⁺" title="正电荷">⁺</button>
      <button class="sym-btn" type="button" data-sym="⁻" title="负电荷">⁻</button>
      <span class="sym-panel__hint">条件：</span>
      <button class="sym-btn" type="button" data-cond="点燃" title="等号上方写点燃">点燃</button>
      <button class="sym-btn" type="button" data-cond="加热" title="等号上方写加热">加热条件</button>
      <button class="sym-btn" type="button" data-cond="高温" title="等号上方写高温">高温</button>
      <button class="sym-btn" type="button" data-cond="催化剂" title="等号上方写催化剂">催化剂</button>
      <button class="sym-btn" type="button" data-cond="电解" title="等号上方写电解">电解</button>
      <button class="sym-btn" type="button" data-cond="光照" title="等号上方写光照">光照</button>
      <input id="condCustom" class="sym-input" maxlength="24" placeholder="自定义条件" aria-label="自定义条件" />
      <button class="sym-btn" type="button" id="btnCondCustom" title="把自定义条件写到等号上方">插入条件</button>
      <button class="sym-btn sym-btn--frac" type="button" id="btnFrac" title="插入分数线（选中 1/2 可直接变上下两行）">
        <span class="frac-ico"><span>a</span><i></i><span>b</span></span>
        <span>分数线</span>
      </button>
    </div>
  </div>
  <div class="submit-bar__in">
    <div class="submit-bar__stat">已答 <b id="doneCount">0</b> / <span id="totalCount">0</span> 题</div>
    <button class="btn btn--ghost btn--sm" id="btnSym" type="button">符号 / 分数线</button>
    <button class="btn" id="btnSubmit">交卷并判分</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="img-viewer" id="imgViewer" aria-hidden="true">
  <button class="img-viewer__close" id="imgViewerClose" type="button" aria-label="关闭预览">×</button>
  <img id="imgViewerImg" alt="图片预览">
  <div class="img-viewer__hint">点击空白处或按 Esc 关闭</div>
</div>

<script>
const PAPER = __PAPER_DATA__;
const TYPE_TEXT = { single: '单选题', multiple: '多选题', fill: '填空题',
                    calculation: '计算题', subjective: '简答题' };
const state = {
  answers: {},        // 题号 → 答案字符串
  finished: false,
  startAt: Date.now(),
  selfJudge: {},      // 非选择题自评
  attemptId: null,    // 服务端作答记录 id
  switchCount: 0,     // 离开答题页次数（反作弊）
  deadline: 0,        // 交卷截止时间戳（服务端给的时间 + 本地时钟）
};

const $ = (id) => document.getElementById(id);
const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, '').toUpperCase()
  .replace(/[，,。．]/g, '.').replace(/[；;]/g, ';');

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2200);
}

/* ---------- 渲染 ---------- */
function renderMeta() {
  const m = [];
  if (PAPER.province) m.push(PAPER.province);
  if (PAPER.year) m.push(PAPER.year + ' 年');
  if (PAPER.exam_type) m.push(PAPER.exam_type);
  m.push(PAPER.questions.length + ' 题');
  m.push('总分 ' + PAPER.total_score);
  m.push('建议 ' + PAPER.duration + ' 分钟');
  $('meta').innerHTML = m.map((x) => '<span>' + x + '</span>').join('');
  $('totalCount').textContent = PAPER.questions.length;
  document.title = PAPER.title;
}

function renderNav() {
  const nav = $('nav');
  PAPER.questions.forEach((q) => {
    const a = document.createElement('a');
    a.href = '#q' + q.no;
    a.textContent = q.no;
    a.dataset.no = q.no;
    a.onclick = (e) => {
      e.preventDefault();
      document.getElementById('q' + q.no).scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    nav.appendChild(a);
  });
}

function hasAnswer(value) {
  if (value == null) return false;
  if (typeof value === 'object') {
    return Object.values(value).some((v) => String(v == null ? '' : v).trim());
  }
  return String(value).trim().length > 0;
}

function updateNav() {
  document.querySelectorAll('.nav a').forEach((a) => {
    const no = a.dataset.no;
    a.classList.toggle('done', hasAnswer(state.answers[no]));
  });
  const done = Object.values(state.answers).filter(hasAnswer).length;
  $('doneCount').textContent = done;
}

function subQuestionsHtml(subs, qNo, prefix, depth) {
  const list = subs || [];
  if (!list.length) return '';
  return '<div class="sub-list">' + list.map(function (sub, i) {
    const path = prefix ? prefix + '.' + i : String(i);
    const label = prefix ? prefix + '.' + (i + 1) : String(i + 1);
    const children = sub.children || [];
    const childHtml = children.length
      ? subQuestionsHtml(children, qNo, path, (depth || 0) + 1)
      : '';
    return '<div class="sub-q" style="margin-left:' + ((depth || 0) * 18) + 'px">' +
      '<div class="sub-q__head">' +
        '<span class="sub-q__no">小问 ' + label + '</span>' +
        '<span class="sub-q__score">' + (sub.score || 0) + ' 分</span>' +
      '</div>' +
      (sub.content ? '<div class="sub-q__content">' + renderMathLite(sub.content) + '</div>' : '') +
      (children.length
        ? childHtml
        : '<textarea class="blank sub-blank" data-no="' + qNo + '" data-sub="' + path +
          '" placeholder="小问 ' + label + ' 答案" rows="2"></textarea>' +
          '<div class="blank-prev"></div>') +
      '</div>';
  }).join('') + '</div>';
}

function renderList() {
  const wrap = $('list');
  PAPER.questions.forEach((q) => {
    const card = document.createElement('div');
    card.className = 'q';
    card.id = 'q' + q.no;

    const isChoice = q.type === 'single' || q.type === 'multiple';
    let optsHtml = '';
    if (isChoice && q.options && q.options.length) {
      optsHtml = '<div class="opts">' + q.options.map((o) => {
        const key = o.key || o.value || '';
        const text = o.text || o.value || '';
        return '<div class="opt" data-no="' + q.no + '" data-key="' + key + '">' +
               '<div class="opt__key">' + key + '</div><div>' + renderMathLite(text) + '</div></div>';
      }).join('') + '</div>';
    }
    let blankHtml = '';
    if (!isChoice) {
      const subs = q.sub_questions || [];
      if (subs.length) {
        blankHtml = subQuestionsHtml(subs, q.no, '', 0);
      } else {
        blankHtml = '<textarea class="blank" data-no="' + q.no +
          '" placeholder="在这里写你的答案（填空/计算/简答）" rows="2"></textarea>' +
          '<div class="blank-prev"></div>';
      }
    }

    // 需要看图的题：优先显示自动裁剪的本题配图，裁剪失败再回退整页
    let figHtml = '';
    if (q.figures && q.figures.length) {
      figHtml =
        '<div class="fig">' +
          q.figures.map(function (name) {
            const src = 'figimg/' + encodeURIComponent(name);
            return '<img class="zoomable" src="' + src + '" alt="第 ' + q.no +
              ' 题配图" loading="lazy" title="点击预览">';
          }).join('') +
          '<div class="fig__tip">本题原题截图（自动切割，含题干与配图；点击预览）</div>' +
        '</div>';
    } else if (q.has_figure && q.page) {
      const src = 'pageimg/' + q.page;
      figHtml =
        '<div class="fig">' +
          '<img class="zoomable" src="' + src + '" alt="原卷第 ' + q.page +
            ' 页" loading="lazy" title="点击预览">' +
          '<div class="fig__tip">原卷配图 · 第 ' + q.page + ' 页（点击预览）</div>' +
        '</div>';
    }

    card.innerHTML =
      '<div class="q__head">' +
        '<div class="q__no">' + q.no + '</div>' +
        '<span class="q__type">' + (TYPE_TEXT[q.type] || '题目') + '</span>' +
        '<span class="q__score">' + (q.score || 0) + ' 分</span>' +
        '<span id="tag' + q.no + '"></span>' +
      '</div>' +
      '<div class="q__title">' + renderMathLite(q.title || '') + '</div>' +
      (q.content ? '<div class="q__content">' + renderMathLite(q.content) + '</div>' : '') +
      figHtml + optsHtml + blankHtml +
      '<div id="ans' + q.no + '"></div>';

    wrap.appendChild(card);
  });

  // 选项点击
  document.querySelectorAll('.opt').forEach((el) => {
    el.onclick = () => {
      if (state.finished) return;
      const no = el.dataset.no;
      const key = el.dataset.key;
      const q = PAPER.questions.find((x) => String(x.no) === String(no));
      if (q.type === 'multiple') {
        const set = new Set((state.answers[no] || '').split('').filter(Boolean));
        set.has(key) ? set.delete(key) : set.add(key);
        state.answers[no] = [...set].sort().join('');
      } else {
        state.answers[no] = key;
      }
      document.querySelectorAll('.opt[data-no="' + no + '"]').forEach((o) => {
        o.classList.toggle('on', (state.answers[no] || '').includes(o.dataset.key));
      });
      updateNav();
    };
  });

  // 填空输入（含多个小问）
  document.querySelectorAll('.blank').forEach((el) => {
    el.oninput = () => {
      updateBlankPreview(el);
      if (state.finished) return;
      const no = el.dataset.no;
      const sub = el.dataset.sub;
      if (sub !== undefined) {
        if (!state.answers[no] || typeof state.answers[no] !== 'object') {
          state.answers[no] = {};
        }
        state.answers[no][sub] = el.value;
      } else {
        state.answers[no] = el.value;
      }
      updateNav();
    };
  });
}

/* 输入框下方的分数预览：只有写了公式才显示 */
function updateBlankPreview(el) {
  if (!el) return;
  const prev = el.nextElementSibling;
  if (!prev || !prev.classList.contains('blank-prev')) return;
  const hasFormula = !!el.value && el.value.indexOf('\\') >= 0;
  prev.innerHTML = hasFormula ? renderMathLite(el.value) : '';
  prev.classList.toggle('show', hasFormula);
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* 轻量公式渲染：只把 $\frac{分子}{分母}$ 画成上下两行，其余文字原样转义。
   套卷页保持单文件、离线可用，所以不引 KaTeX。 */
function renderMathLite(text) {
  const src = String(text == null ? '' : text).replace(/\$([^$\n]+)\$/g, '$1');
  let i = 0;

  function group() {
    if (src[i] !== '{') return null;
    i += 1;
    return parse(true);
  }

  function parse(stop) {
    let html = '';
    let buf = '';
    const flush = () => { if (buf) { html += esc(buf); buf = ''; } };
    while (i < src.length) {
      const ch = src[i];
      if (stop && ch === '}') { i += 1; flush(); return html; }
      if (ch === '\\' && src.substr(i, 5) === '\\frac') {
        const save = i;
        i += 5;
        const num = group();
        const den = num == null ? null : group();
        if (num == null || den == null) { i = save + 1; buf += '\\'; continue; }
        flush();
        html += '<span class="mfrac"><span class="mfrac__n">' + num +
                '</span><span class="mfrac__d">' + den + '</span></span>';
        continue;
      }
      if (ch === '\\' && src.substr(i, 9) === '\\overset{') {
        const end = src.indexOf('}{=}', i + 9);
        if (end > 0) {
          const condition = src.slice(i + 9, end);
          flush();
          html += '<span class="mcond"><span class="mcond__txt">' + esc(condition) +
                  '</span><span class="mcond__arrow">=</span></span>';
          i = end + 4;
          continue;
        }
      }
      buf += ch;
      i += 1;
    }
    flush();
    return stop ? null : html;
  }

  const html = parse(false);
  return html == null ? esc(src) : html;
}

/* ---------- 倒计时：以服务端给的截止时间为准 ----------
   浏览器会把后台标签的定时器降到 1 次/分钟，如果用递减计数器，
   学生切到别的标签就等于「停表」。所以每次都用绝对时间重算。 */
function renderTimer() {
  if (state.finished) return;
  const left = Math.max(0, Math.round((state.deadline - Date.now()) / 1000));
  const m = Math.floor(left / 60);
  const s = left % 60;
  const t = $('timer');
  t.textContent = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  t.className = 'timer' + (left <= 60 ? ' danger' : left <= 300 ? ' warn' : '');
  if (left <= 0) {
    toast('时间到，自动交卷');
    submit(true);
  }
}

async function initTimer() {
  let remain = (PAPER.duration || 75) * 60;
  try {
    const token = localStorage.getItem('token');
    const r = await fetch('start', {
      method: 'POST',
      headers: token ? { Authorization: 'Bearer ' + token } : {},
    });
    if (r.ok) {
      const d = await r.json();
      state.attemptId = d.attempt_id;
      state.switchCount = d.switch_count || 0;
      remain = d.remain_sec != null ? d.remain_sec : remain;
      if (state.switchCount) showCheatChip();
      if (remain <= 0) {
        toast('本次作答时间已用完，直接交卷');
        state.deadline = Date.now();
        renderTimer();
        return;
      }
    }
  } catch (e) { /* 离线兜底：本地计时 */ }
  state.deadline = Date.now() + remain * 1000;
  renderTimer();
}

/* ---------- 反作弊 ---------- */
function showCheatChip() {
  const el = $('cheatChip');
  if (!state.switchCount) { el.style.display = 'none'; return; }
  el.textContent = '离开 ' + state.switchCount + ' 次';
  el.style.display = '';
}

document.addEventListener('visibilitychange', () => {
  if (state.finished) return;
  if (document.hidden) {
    state.switchCount++;
    showCheatChip();
    if (state.switchCount >= 5) {
      toast('多次离开答题页，已自动交卷');
      submit(true);
    } else if (state.switchCount >= 3) {
      toast('第 ' + state.switchCount + ' 次切屏，再切屏将自动交卷');
    } else {
      toast('检测到离开答题页，答题期间请勿切屏');
    }
  } else {
    renderTimer();   // 回到页面立刻校正倒计时
  }
});

// 答题期间禁止复制题目 / 粘贴答案 / 右键
['copy', 'cut', 'contextmenu', 'paste'].forEach((ev) => {
  document.addEventListener(ev, (e) => {
    if (state.finished) return;
    e.preventDefault();
    if (ev === 'paste') toast('请手动输入答案');
    else if (ev !== 'contextmenu') toast('答题期间不支持复制题目');
  });
});

// 提前离开提醒（防止手滑关掉）
window.addEventListener('beforeunload', (e) => {
  if (state.finished) return;
  e.preventDefault();
  e.returnValue = '';
});

/* ---------- 本地判分（离线兜底 & 提交失败降级） ---------- */
function localJudge() {
  let score = 0, right = 0, wrong = 0;
  const details = [];
  PAPER.questions.forEach((q) => {
    const mine = state.answers[q.no] || '';
    const isChoice = q.type === 'single' || q.type === 'multiple';
    let ok = null;
    if (isChoice && mine) ok = norm(mine) === norm(q.answer);
    if (isChoice && !mine) ok = false;
    if (ok === true) { score += q.score || 0; right++; }
    else if (ok === false) { wrong++; }
    details.push({ no: q.no, ok, answer: q.answer, mine });
  });
  return { score, right, wrong, details };
}

/* ---------- 提交 ---------- */
async function submit(auto) {
  if (state.finished) return;
  if (!auto) {
    const done = Object.values(state.answers).filter(hasAnswer).length;
    if (done < PAPER.questions.length && !confirm('还有 ' + (PAPER.questions.length - done) + ' 题没答，确定交卷？')) return;
  }
  state.finished = true;
  $('btnSubmit').disabled = true;
  $('btnSubmit').textContent = '判分中…';
  $('btnTop').disabled = true;

  const used = Math.round((Date.now() - state.startAt) / 1000);
  const payload = {
    answers: state.answers,
    duration_sec: used,
    self_judge: state.selfJudge,
    attempt_id: state.attemptId,
    switch_count: state.switchCount,
  };

  let data = null;
  try {
    const token = localStorage.getItem('token');
    const resp = await fetch('submit', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' },
        token ? { Authorization: 'Bearer ' + token } : {}),
      body: JSON.stringify(payload),
    });
    if (resp.ok) data = await resp.json();
  } catch (e) { /* 离线或跨域，走本地判分 */ }

  if (!data) {
    const local = localJudge();
    data = {
      score: local.score, total_score: PAPER.total_score,
      correct_count: local.right, wrong_count: local.wrong,
      offline: true, details: local.details,
    };
    toast('未连接到服务器，成绩只在本地显示（错题未上传）');
  }

  showResult(data, used);
}

function showResult(d, used) {
  const box = $('resultBox');
  const pct = d.total_score ? Math.round(d.score / d.total_score * 100) : 0;
  box.innerHTML =
    '<div class="result">' +
      '<div class="result__score">' + d.score + '<small> / ' + d.total_score + '</small></div>' +
      '<div class="result__row">' +
        '<div><b>' + (d.correct_count ?? 0) + '</b>答对</div>' +
        '<div><b>' + (d.wrong_count ?? 0) + '</b>答错</div>' +
        '<div><b>' + (used < 60 ? '<1' : Math.round(used / 60)) + '</b>用时(分)</div>' +
        '<div><b>' + pct + '%</b>得分率</div>' +
      '</div>' +
      '<div class="result__tip">' +
        (d.overtime ? '本次作答超过规定时长；' : '') +
        (d.switch_count ? '答题期间离开页面 ' + d.switch_count + ' 次；' : '') +
        (d.missing_answer_count ? d.missing_answer_count + ' 题参考答案缺失，未计入总分；' : '') +
        (d.offline
          ? '本次为离线判分，错题没有同步到错题本'
          : '错题已同步到你的错题本，可在「错题本」里复习') +
      '</div>' +
    '</div>';

  // 逐题标注
  (d.details || []).forEach((item) => {
    const q = PAPER.questions.find((x) => String(x.no) === String(item.no));
    if (!q) return;
    const card = $('q' + item.no);
    const tag = $('tag' + item.no);
    if (item.ok === true) { card.classList.add('right'); tag.innerHTML = '<span class="tag right">正确</span>'; }
    else if (item.ok === false) { card.classList.add('wrong'); tag.innerHTML = '<span class="tag wrong">错误</span>'; }

    if (q.options && q.options.length) {
      document.querySelectorAll('.opt[data-no="' + item.no + '"]').forEach((o) => {
        const k = o.dataset.key;
        if (String(q.answer || '').includes(k)) o.classList.add('correct');
        else if ((state.answers[item.no] || '').includes(k)) o.classList.add('mistake');
      });
    }
    const mineIsObj = item.mine && typeof item.mine === 'object';
    const mineText = mineIsObj
      ? Object.values(item.mine).filter((v) => String(v || '').trim()).map((v) => renderMathLite(v)).join('；') || '未作答'
      : (hasAnswer(item.mine) ? renderMathLite(String(item.mine)) : '未作答');
    const subHtml = (item.sub_results || []).map(function (sub, i) {
      const label = sub.path || (i + 1);
      return '<div class="ans__row">小问 ' + label + '：' +
        (sub.mine ? renderMathLite(sub.mine) : '未作答') +
        (sub.ok ? ' <span class="ok">✓</span>' : ' <span class="no">✗</span>') +
        ' <span style="color:var(--text-3);font-size:12px;">得分 ' + (sub.earned || 0) + '/' + (sub.score || 0) + '</span></div>';
    }).join('');
    $('ans' + item.no).innerHTML =
      '<div class="ans">' +
        '<div class="ans__row">你的答案：<b class="' + (item.ok === true ? 'ok' : item.ok === false ? 'no' : '') + '">' +
          mineText + '</b></div>' +
        subHtml +
        '<div class="ans__row">正确答案：<b class="ok">' + renderMathLite(item.answer || '—') + '</b></div>' +
        (q.analysis ? '<div class="ans__row">解析：' + renderMathLite(q.analysis) + '</div>' : '') +
        (item.reason ? '<div class="ans__row ans__reason">判分说明：' + esc(item.reason) + '</div>' : '') +
      '</div>';
  });

  $('submitBar').style.display = 'none';
  // 交卷后锁住填空框，避免看起来还能改
  document.querySelectorAll('.blank').forEach((el) => { el.readOnly = true; });
  document.querySelectorAll('.blank-prev').forEach((el) => el.classList.remove('show'));
  document.getElementById('btnSubmit') && (document.getElementById('btnSubmit').style.display = 'none');
  document.getElementById('btnTop') && (document.getElementById('btnTop').style.display = 'none');
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- 图片预览（页面内，不新开标签页，避免误判切屏） ---------- */
const imgViewer = $('imgViewer');
const imgViewerImg = $('imgViewerImg');
let bodyOverflowBeforeViewer = '';

function openImageViewer(src) {
  if (!src) return;
  bodyOverflowBeforeViewer = document.body.style.overflow;
  imgViewerImg.src = src;
  imgViewer.classList.add('open');
  imgViewer.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeImageViewer() {
  imgViewer.classList.remove('open');
  imgViewer.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = bodyOverflowBeforeViewer;
}

document.addEventListener('click', (event) => {
  const img = event.target.closest && event.target.closest('img.zoomable');
  if (img) {
    event.preventDefault();
    openImageViewer(img.currentSrc || img.src);
    return;
  }
  if (event.target === imgViewer) closeImageViewer();
});
$('imgViewerClose').addEventListener('click', closeImageViewer);
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && imgViewer.classList.contains('open')) closeImageViewer();
});

/* ---------- 符号 / 分数线插入 ---------- */
let activeBlank = null;
document.addEventListener('focusin', (event) => {
  const el = event.target;
  if (el && el.classList && el.classList.contains('blank')) activeBlank = el;
});

function insertAtBlank(text, caretOffset) {
  const el = activeBlank;
  if (!el || el.readOnly || state.finished) {
    toast('请先点一下答案框，再点符号');
    return;
  }
  const start = typeof el.selectionStart === 'number' ? el.selectionStart : el.value.length;
  const end = typeof el.selectionEnd === 'number' ? el.selectionEnd : start;
  el.setRangeText(text, start, end, 'end');
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.focus();
  try {
    const pos = Math.min(start + caretOffset, el.value.length);
    el.setSelectionRange(pos, pos);
  } catch (err) { /* 忽略不支持选区的输入框 */ }
}

function insertFraction() {
  const el = activeBlank;
  if (!el || el.readOnly || state.finished) {
    toast('请先点一下答案框，再点分数线');
    return;
  }
  const start = typeof el.selectionStart === 'number' ? el.selectionStart : el.value.length;
  const end = typeof el.selectionEnd === 'number' ? el.selectionEnd : start;
  const picked = el.value.slice(start, end).trim();
  const slash = picked.indexOf('/');
  let latex;
  let caret;
  if (picked && slash > 0 && slash === picked.lastIndexOf('/')) {
    // 选中 "1/2" 这类写法：直接拆成分子分母
    latex = '$\\frac{' + picked.slice(0, slash).trim() + '}{' + picked.slice(slash + 1).trim() + '}$';
    caret = latex.length;
  } else if (picked) {
    // 选中一段文字：当分子，光标进分母
    latex = '$\\frac{' + picked + '}{}$';
    caret = latex.length - 2;
  } else {
    // 没选中：插空分数，光标进分子
    latex = '$\\frac{}{}$';
    caret = 7;
  }
  insertAtBlank(latex, caret);
}

function insertCondition(condition) {
  const el = activeBlank;
  if (!el || el.readOnly || state.finished) {
    toast('请先点一下答案框，再点条件');
    return;
  }
  const start = typeof el.selectionStart === 'number' ? el.selectionStart : el.value.length;
  const end = typeof el.selectionEnd === 'number' ? el.selectionEnd : start;
  let from = start;
  let to = end;
  const picked = el.value.slice(start, end);
  if (!picked.trim()) {
    let i = start - 1;
    while (i >= 0 && /\s/.test(el.value[i])) i -= 1;
    if (el.value[i] === '=') {
      from = i;
      to = i + 1;
    }
  }
  const expr = '$\\overset{' + condition + '}{=}$';
  try { el.setSelectionRange(from, to); } catch (err) { /* 忽略 */ }
  insertAtBlank(expr, expr.length);
}

const symPanel = $('symPanel');
$('btnSym').addEventListener('click', () => {
  symPanel.classList.toggle('open');
});
document.querySelectorAll('.sym-btn').forEach((btn) => {
  // 用 pointerdown 阻止默认行为，别把答案框的焦点和光标抢走
  btn.addEventListener('pointerdown', (event) => event.preventDefault());
  btn.addEventListener('click', () => {
    if (btn.id === 'btnCondCustom') return;
    if (btn.id === 'btnFrac') { insertFraction(); return; }
    const cond = btn.getAttribute('data-cond');
    if (cond) {
      insertCondition(cond);
      return;
    }
    const sym = btn.getAttribute('data-sym') || btn.textContent;
    insertAtBlank(sym, sym.length);
  });
});

const condCustom = $('condCustom');
$('btnCondCustom') && $('btnCondCustom').addEventListener('click', () => {
  const cond = String(condCustom.value || '').trim().replace(/[\[\]{}\\]/g, '');
  if (!cond) {
    toast('先输入条件，例如：浓硫酸 / Δ');
    return;
  }
  insertCondition(cond);
  condCustom.value = '';
});

/* ---------- 启动 ---------- */
renderMeta();
renderNav();
renderList();
updateNav();
initTimer();
setInterval(renderTimer, 500);
$('btnSubmit').onclick = () => submit(false);
$('btnTop').onclick = () => submit(false);

// 记录访问（失败不影响做题）
try {
  fetch('view', { method: 'POST' }).catch(() => {});
} catch (e) {}
</script>
</body>
</html>
"""
