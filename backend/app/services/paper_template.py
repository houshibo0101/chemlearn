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

  /* 原卷配图 */
  .fig { margin-top: 12px; }
  .fig img {
    max-width: 100%; max-height: 560px; object-fit: contain; display: block;
    border: 1px solid var(--line); border-radius: 10px; background: #fff;
  }
  .fig__tip { font-size: 11.5px; color: var(--text-3); margin-top: 6px; }

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
    <a class="bar__back" href="../../../app/papers" title="返回套卷列表">←</a>
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
  <div class="submit-bar__in">
    <div class="submit-bar__stat">已答 <b id="doneCount">0</b> / <span id="totalCount">0</span> 题</div>
    <button class="btn" id="btnSubmit">交卷并判分</button>
  </div>
</div>

<div class="toast" id="toast"></div>

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

function updateNav() {
  document.querySelectorAll('.nav a').forEach((a) => {
    const no = a.dataset.no;
    a.classList.toggle('done', !!(state.answers[no] && String(state.answers[no]).trim()));
  });
  const done = Object.values(state.answers).filter((v) => v && String(v).trim()).length;
  $('doneCount').textContent = done;
}

function renderList() {
  const wrap = $('list');
  PAPER.questions.forEach((q) => {
    const card = document.createElement('div');
    card.className = 'q';
    card.id = 'q' + q.no;

    let optsHtml = '';
    if (q.options && q.options.length) {
      optsHtml = '<div class="opts">' + q.options.map((o) => {
        const key = o.key || o.value || '';
        const text = o.text || o.value || '';
        return '<div class="opt" data-no="' + q.no + '" data-key="' + key + '">' +
               '<div class="opt__key">' + key + '</div><div>' + esc(text) + '</div></div>';
      }).join('') + '</div>';
    }
    let blankHtml = '';
    if (!q.options || !q.options.length) {
      blankHtml = '<textarea class="blank" data-no="' + q.no +
        '" placeholder="在这里写你的答案（填空/计算/简答）" rows="2"></textarea>';
    }

    // 需要看图的题：附上原卷对应页（文字抽取拿不到装置图/曲线图）
    let figHtml = '';
    if (q.has_figure && q.page) {
      const src = 'pageimg/' + q.page;
      figHtml =
        '<div class="fig">' +
          '<a href="' + src + '" target="_blank" title="点击查看原卷页面">' +
            '<img src="' + src + '" alt="原卷第 ' + q.page + ' 页" loading="lazy">' +
          '</a>' +
          '<div class="fig__tip">原卷配图 · 第 ' + q.page + ' 页（点击放大）</div>' +
        '</div>';
    }

    card.innerHTML =
      '<div class="q__head">' +
        '<div class="q__no">' + q.no + '</div>' +
        '<span class="q__type">' + (TYPE_TEXT[q.type] || '题目') + '</span>' +
        '<span class="q__score">' + (q.score || 0) + ' 分</span>' +
        '<span id="tag' + q.no + '"></span>' +
      '</div>' +
      '<div class="q__title">' + esc(q.title || '') + '</div>' +
      (q.content ? '<div class="q__content">' + esc(q.content) + '</div>' : '') +
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

  // 填空输入
  document.querySelectorAll('.blank').forEach((el) => {
    el.oninput = () => {
      if (state.finished) return;
      state.answers[el.dataset.no] = el.value;
      updateNav();
    };
  });
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
    const done = Object.values(state.answers).filter((v) => v && String(v).trim()).length;
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
    $('ans' + item.no).innerHTML =
      '<div class="ans">' +
        '<div class="ans__row">你的答案：<b class="' + (item.ok === true ? 'ok' : item.ok === false ? 'no' : '') + '">' +
          (item.mine ? esc(item.mine) : '未作答') + '</b></div>' +
        '<div class="ans__row">正确答案：<b class="ok">' + esc(item.answer || '—') + '</b></div>' +
        (q.analysis ? '<div class="ans__row">解析：' + esc(q.analysis) + '</div>' : '') +
        (item.reason ? '<div class="ans__row ans__reason">判分说明：' + esc(item.reason) + '</div>' : '') +
      '</div>';
  });

  $('submitBar').style.display = 'none';
  // 交卷后锁住填空框，避免看起来还能改
  document.querySelectorAll('.blank').forEach((el) => { el.readOnly = true; });
  document.getElementById('btnSubmit') && (document.getElementById('btnSubmit').style.display = 'none');
  document.getElementById('btnTop') && (document.getElementById('btnTop').style.display = 'none');
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

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
